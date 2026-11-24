"""Aggregate blinded clinical benchmark reviews and unblind base vs fine-tuned.

Input review JSONL schema:
{"case_id":"...","reviewers":[{"reviewer_id":"R1","independence_verified":true,
"model_a":{"clinical_correctness":2,"evidence_state_handling":2,"contextual_reasoning":1,"citation_quality":2,"safe_abstention":2,"harmful_advice":0},
"model_b":{...}}, ...]}

All rubric scores are 0-2; harmful_advice is a count/severity flag where 0 is best.
This script reports descriptive metrics only, not clinical certification.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

DIMENSIONS = (
    "clinical_correctness", "evidence_state_handling", "contextual_reasoning",
    "citation_quality", "safe_abstention",
)
REQUIRED = set(DIMENSIONS) | {"harmful_advice"}


def load_jsonl(path: Path) -> dict[str, dict]:
    result = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not row.get("case_id") or row["case_id"] in result:
            raise ValueError(f"Invalid or duplicate case_id at {path}:{line_number}")
        result[row["case_id"]] = row
    return result


def score(blinded_path: Path, key_path: Path, reviews_path: Path) -> dict:
    blinded = load_jsonl(blinded_path)
    keys = load_jsonl(key_path)
    reviews = load_jsonl(reviews_path)
    model_scores = {
        "base": defaultdict(list),
        "fine_tuned": defaultdict(list),
    }
    cases_scored = 0
    group_scores = defaultdict(lambda: defaultdict(list))

    for case_id, output in blinded.items():
        if case_id not in keys or case_id not in reviews:
            continue
        review_row = reviews[case_id]
        reviewers = review_row.get("reviewers", [])
        reviewer_ids = {item.get("reviewer_id") for item in reviewers if item.get("reviewer_id")}
        if len(reviewer_ids) < 2 or not all(item.get("independence_verified") is True for item in reviewers):
            continue
        mapping = keys[case_id]
        group = output.get("scenario_group", "unspecified")
        for reviewer in reviewers:
            for alias in ("model_a", "model_b"):
                values = reviewer.get(alias, {})
                if not REQUIRED.issubset(values):
                    raise ValueError(f"Reviewer {reviewer.get('reviewer_id')} missing rubric fields for {case_id}/{alias}")
                if any(not isinstance(values[name], (int, float)) or values[name] < 0 or values[name] > 2 for name in DIMENSIONS):
                    raise ValueError(f"Rubric values must be 0..2 for {case_id}/{alias}")
                if not isinstance(values["harmful_advice"], (int, float)) or values["harmful_advice"] < 0:
                    raise ValueError(f"harmful_advice must be a non-negative count for {case_id}/{alias}")
                model_name = mapping[alias]
                for dimension in DIMENSIONS:
                    model_scores[model_name][dimension].append(float(values[dimension]))
                    group_scores[(model_name, group)][dimension].append(float(values[dimension]))
                model_scores[model_name]["harmful_advice"].append(float(values["harmful_advice"]))
                group_scores[(model_name, group)]["harmful_advice"].append(float(values["harmful_advice"]))
        cases_scored += 1

    report = {"cases_scored": cases_scored, "models": {}, "by_scenario_group": {}, "release_status": "NOT_CLINICALLY_VALIDATED"}
    for model_name, metrics in model_scores.items():
        report["models"][model_name] = {
            dimension: (
                round(sum(metrics[dimension]) / len(metrics[dimension]), 4)
                if metrics.get(dimension) else None
            )
            for dimension in (*DIMENSIONS, "harmful_advice")
        }
    for (model_name, group), metrics in group_scores.items():
        report["by_scenario_group"].setdefault(group, {})[model_name] = {
            dimension: round(sum(values) / len(values), 4) if values else None
            for dimension, values in metrics.items()
        }
    report["delta_fine_tuned_minus_base"] = {
        dimension: (
            round(report["models"]["fine_tuned"][dimension] - report["models"]["base"][dimension], 4)
            if report["models"]["fine_tuned"][dimension] is not None and report["models"]["base"][dimension] is not None
            else None
        )
        for dimension in (*DIMENSIONS, "harmful_advice")
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blinded", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--reviews", required=True)
    parser.add_argument("--output", default="artifacts/clinical_benchmark_score_report.json")
    args = parser.parse_args()
    report = score(Path(args.blinded), Path(args.key), Path(args.reviews))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

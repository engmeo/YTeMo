"""Paired Clinical Benchmark runner with blinded human-review handoff.

This runner measures latency and collects outputs. It does NOT assign clinical
correctness automatically. Human reviewers must score anonymized outputs using
the rubric in docs/CLINICAL_MODEL_TRAINING.vi.md.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from pathlib import Path

import requests


def call_model(base_url: str, model: str, api_key: str, prompt: str, timeout: int) -> tuple[str, float]:
    started = time.perf_counter()
    response = requests.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 900,
        },
        timeout=(5, timeout),
    )
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"]
    if isinstance(text, list):
        text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
    return str(text), round((time.perf_counter() - started) * 1000, 1)


def run(cases_path: Path, output_path: Path, timeout: int) -> dict:
    base_url = os.environ["BENCH_BASE_URL"]
    tuned_url = os.environ["BENCH_TUNED_URL"]
    base_model = os.environ["BENCH_BASE_MODEL"]
    tuned_model = os.environ["BENCH_TUNED_MODEL"]
    base_key = os.getenv("BENCH_BASE_API_KEY", "local")
    tuned_key = os.getenv("BENCH_TUNED_API_KEY", "local")
    rows = []
    latencies = {"base": [], "fine_tuned": []}

    for line_number, line in enumerate(cases_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        case = json.loads(line)
        if not case.get("case_id") or not case.get("prompt") or not case.get("scenario_group"):
            raise ValueError(f"Case line {line_number} must include case_id, prompt, scenario_group.")
        base_text, base_ms = call_model(base_url, base_model, base_key, case["prompt"], timeout)
        tuned_text, tuned_ms = call_model(tuned_url, tuned_model, tuned_key, case["prompt"], timeout)
        latencies["base"].append(base_ms)
        latencies["fine_tuned"].append(tuned_ms)
        rows.append({
            "case_id": case["case_id"],
            "scenario_group": case["scenario_group"],
            "evidence_state": case.get("evidence_state", "UNSPECIFIED"),
            "must_abstain": bool(case.get("must_abstain", False)),
            "base": {"text": base_text, "latency_ms": base_ms},
            "fine_tuned": {"text": tuned_text, "latency_ms": tuned_ms},
            "blind_review": {"base_alias": "A", "fine_tuned_alias": "B", "review_status": "PENDING"},
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    summary = {
        "cases": len(rows),
        "base_latency_median_ms": statistics.median(latencies["base"]) if rows else None,
        "fine_tuned_latency_median_ms": statistics.median(latencies["fine_tuned"]) if rows else None,
        "base_latency_p95_ms": sorted(latencies["base"])[max(0, int(len(rows) * 0.95) - 1)] if rows else None,
        "fine_tuned_latency_p95_ms": sorted(latencies["fine_tuned"])[max(0, int(len(rows) * 0.95) - 1)] if rows else None,
        "clinical_quality": "NOT_SCORED_REQUIRES_BLINDED_HUMAN_REVIEW",
        "output": str(output_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", default="artifacts/clinical_benchmark_outputs.jsonl")
    parser.add_argument("--timeout", type=int, default=25)
    args = parser.parse_args()
    run(Path(args.cases), Path(args.output), max(5, min(args.timeout, 60)))


if __name__ == "__main__":
    main()

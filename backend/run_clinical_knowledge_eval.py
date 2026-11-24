"""Run the deterministic Clinical Knowledge retrieval evaluation harness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from clinical_knowledge_evaluation import evaluate_dataset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True, help="Expert-adjudicated cases JSON")
    parser.add_argument("--results", required=True, help="Mapping case_id -> retrieval result JSON")
    parser.add_argument("--output", default=None, help="Optional report output path")
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    report = evaluate_dataset(cases, results)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

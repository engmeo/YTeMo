"""Prepare deduplicated, provenance-preserving clinical SFT JSONL.

Input JSONL is a curated record format, not raw document ingestion. Never point
this script at patient records or bulk PDFs. Each record must have a license,
source URL, privacy review, and clinical review state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

DEFAULT_LICENSES = {"CC0-1.0", "CC-BY-4.0", "CC-BY-3.0", "US-GOV-PD"}
EVIDENCE_STATES = {"STRONG", "WEAK", "CONFLICTING", "INSUFFICIENT"}


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    return re.sub(r"\s+", " ", value).strip()


def record_key(record: dict) -> str:
    canonical = "\n".join(
        normalize_text(str(record.get(key, ""))).casefold()
        for key in ("instruction", "input", "response", "evidence_state")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_record(record: dict, allowed_licenses: set[str]) -> list[str]:
    errors = []
    for field in ("instruction", "response", "source_url", "license", "source_id"):
        if not normalize_text(str(record.get(field, ""))):
            errors.append(f"missing_{field}")
    if record.get("license") not in allowed_licenses:
        errors.append("license_not_allowlisted")
    if record.get("evidence_state") not in EVIDENCE_STATES:
        errors.append("invalid_evidence_state")
    if record.get("clinical_review_status") != "APPROVED_FOR_TRAINING":
        errors.append("clinical_review_required")
    if record.get("privacy_reviewed") is not True:
        errors.append("privacy_review_required")
    if record.get("source_verified") is not True:
        errors.append("source_verification_required")
    if record.get("contains_patient_data") is True:
        errors.append("patient_data_forbidden_in_default_training_pipeline")
    return errors


def prepare(input_path: Path, output_path: Path, reject_path: Path, licenses: set[str]) -> dict:
    seen = set()
    accepted = []
    rejected = []
    for line_number, line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            rejected.append({"line": line_number, "errors": ["invalid_json"]})
            continue
        errors = validate_record(record, licenses)
        key = record_key(record)
        if key in seen:
            errors.append("duplicate_content")
        if errors:
            rejected.append({"line": line_number, "source_id": record.get("source_id"), "errors": errors})
            continue
        seen.add(key)
        accepted.append({
            "instruction": normalize_text(record["instruction"]),
            "input": normalize_text(str(record.get("input", ""))),
            "response": normalize_text(record["response"]),
            "evidence_state": record["evidence_state"],
            "evidence_summary": normalize_text(str(record.get("evidence_summary", ""))),
            "source_id": record["source_id"],
            "source_url": record["source_url"],
            "license": record["license"],
            "license_url": record.get("license_url"),
            "source_version": record.get("source_version"),
            "source_hash": record.get("source_hash"),
            "clinical_review_id": record.get("clinical_review_id"),
            "reviewer_count": record.get("reviewer_count", 0),
            "privacy_reviewed": True,
            "training_record_sha256": key,
        })
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in accepted), encoding="utf-8")
    reject_path.parent.mkdir(parents=True, exist_ok=True)
    reject_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rejected), encoding="utf-8")
    return {"accepted": len(accepted), "rejected": len(rejected), "deduplicated": sum("duplicate_content" in row["errors"] for row in rejected)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="artifacts/clinical_sft.jsonl")
    parser.add_argument("--rejects", default="artifacts/clinical_sft_rejected.jsonl")
    parser.add_argument("--allow-licenses", default=",".join(sorted(DEFAULT_LICENSES)))
    args = parser.parse_args()
    result = prepare(Path(args.input), Path(args.output), Path(args.rejects), set(args.allow_licenses.split(",")))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

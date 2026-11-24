"""Deterministic evaluation harness for evidence retrieval.

This evaluates retrieval/citation behavior against expert-adjudicated gold cases.
It does not determine clinical truth and does not use an LLM as a judge.
"""
from __future__ import annotations

import re
from typing import Any


def _normalize(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def evaluate_case(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    actual_items = result.get("evidence") or []
    actual_ids = {str(item.get("claim", {}).get("id")) for item in actual_items if item.get("claim", {}).get("id")}
    expected_ids = {str(item) for item in case.get("expected_claim_ids", [])}
    forbidden_ids = {str(item) for item in case.get("forbidden_claim_ids", [])}
    stale_document_ids = {str(item) for item in case.get("stale_document_ids", [])}
    population_mismatch_ids = {str(item) for item in case.get("population_mismatch_claim_ids", [])}
    scope_mismatch_ids = {str(item) for item in case.get("scope_mismatch_claim_ids", [])}
    unresolved_conflict_ids = {str(item) for item in case.get("unresolved_conflict_claim_ids", [])}
    true_positive = len(actual_ids & expected_ids)
    precision = true_positive / len(actual_ids) if actual_ids else (1.0 if not expected_ids else 0.0)
    recall = true_positive / len(expected_ids) if expected_ids else (1.0 if not actual_ids else 0.0)
    expected_abstention = bool(case.get("expected_abstention", False))
    actual_abstention = bool(result.get("abstention", not bool(actual_items)))

    citation_expectations = {
        str(item["claim_id"]): item for item in case.get("expected_citations", [])
    }
    citation_checks = []
    for item in actual_items:
        claim = item.get("claim") or {}
        citation = item.get("citation") or {}
        claim_id = str(claim.get("id") or "")
        document = item.get("document") or {}
        expected = citation_expectations.get(claim_id)
        valid = bool(
            expected
            and str(document.get("id")) == str(expected.get("document_id"))
            and document.get("version") == expected.get("version")
            and citation.get("page") == expected.get("page")
            and _normalize(citation.get("exact_quote")) == _normalize(expected.get("exact_quote"))
            and citation.get("source_url") == expected.get("source_url")
        )
        citation_checks.append(valid)

    return {
        "case_id": case.get("case_id"),
        "precision_at_k": precision,
        "recall_at_k": recall,
        "citation_correctness": (
            sum(citation_checks) / len(citation_checks) if citation_checks else (1.0 if not actual_items else 0.0)
        ),
        "abstention_correct": actual_abstention == expected_abstention,
        "forbidden_claim_ids_returned": sorted(actual_ids & forbidden_ids),
        "unexpected_claim_ids_returned": sorted(actual_ids - expected_ids),
        "stale_document_ids_returned": sorted({str((item.get("document") or {}).get("id")) for item in actual_items} & stale_document_ids),
        "population_mismatch_claim_ids_returned": sorted(actual_ids & population_mismatch_ids),
        "scope_mismatch_claim_ids_returned": sorted(actual_ids & scope_mismatch_ids),
        "unresolved_conflict_claim_ids_returned": sorted(actual_ids & unresolved_conflict_ids),
        "actual_abstention": actual_abstention,
        "expected_abstention": expected_abstention,
    }


def evaluate_dataset(cases: list[dict[str, Any]], results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    eligible, excluded = [], []
    for case in cases:
        reviewers = {
            str(item.get("reviewer_id"))
            for item in case.get("expert_reviews", [])
            if item.get("reviewer_id") and item.get("credential_verified") and item.get("decision") == "ADJUDICATED_INPUT"
        }
        if case.get("adjudication_status") != "ADJUDICATED" or len(reviewers) < 2:
            excluded.append(case.get("case_id"))
            continue
        result = results.get(str(case.get("case_id")))
        if result is None:
            excluded.append(case.get("case_id"))
            continue
        eligible.append(evaluate_case(case, result))

    def mean(key):
        values = [float(item[key]) for item in eligible]
        return sum(values) / len(values) if values else None

    return {
        "eligible_case_count": len(eligible),
        "excluded_case_ids": excluded,
        "metrics": {
            "mean_precision_at_k": mean("precision_at_k"),
            "mean_recall_at_k": mean("recall_at_k"),
            "mean_citation_correctness": mean("citation_correctness"),
            "abstention_accuracy": mean("abstention_correct"),
            "forbidden_claim_return_count": sum(len(item["forbidden_claim_ids_returned"]) for item in eligible),
            "unexpected_claim_return_count": sum(len(item["unexpected_claim_ids_returned"]) for item in eligible),
            "stale_source_return_count": sum(len(item["stale_document_ids_returned"]) for item in eligible),
            "population_mismatch_return_count": sum(len(item["population_mismatch_claim_ids_returned"]) for item in eligible),
            "scope_mismatch_return_count": sum(len(item["scope_mismatch_claim_ids_returned"]) for item in eligible),
            "unresolved_conflict_return_count": sum(len(item["unresolved_conflict_claim_ids_returned"]) for item in eligible),
        },
        "case_results": eligible,
        "notice": "Only expert-adjudicated cases with at least two distinct credential-verified reviewers are scored. These metrics measure retrieval/citation behavior, not clinical safety or correctness.",
    }

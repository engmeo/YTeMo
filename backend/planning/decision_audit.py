"""Auditable decision verification and benchmark integration.

This module is domain-neutral. It verifies decision-result consistency
and adapts decision outcomes to the shared planning benchmark contracts.
It never executes selected actions.
"""
from math import isfinite

from .benchmark import BenchmarkCaseResult
from .decision_engine import DecisionResult, DecisionStatus


def verify_decision_result(
    result: DecisionResult,
    *,
    expected_belief_revision: int,
    expected_world_revision: int | None = None,
) -> tuple[str, ...]:
    """Return audit issues for a decision result and its provenance."""
    if not isinstance(result, DecisionResult):
        raise TypeError("result must be a DecisionResult")

    if (
        isinstance(expected_belief_revision, bool)
        or not isinstance(expected_belief_revision, int)
        or expected_belief_revision < 0
    ):
        raise ValueError("expected_belief_revision must be a non-negative integer")

    if expected_world_revision is not None and (
        isinstance(expected_world_revision, bool)
        or not isinstance(expected_world_revision, int)
        or expected_world_revision < 0
    ):
        raise ValueError("expected_world_revision must be None or a non-negative integer")

    issues = []
    trace = result.trace

    if trace.belief_revision != expected_belief_revision:
        issues.append("belief revision does not match the audited revision")

    if (
        expected_world_revision is not None
        and trace.world_revision != expected_world_revision
    ):
        issues.append("world revision does not match the audited revision")

    evaluations = {item.action_id: item for item in result.evaluations}

    if result.status in (DecisionStatus.SELECTED, DecisionStatus.HUMAN_REVIEW):
        selected = evaluations.get(result.selected_action_id)

        if selected is None:
            issues.append("selected action has no corresponding evaluation")
        elif not selected.feasible:
            issues.append("selected action is marked infeasible")

    elif result.selected_action_id is not None:
        issues.append("non-selection outcome unexpectedly contains an action")

    if result.status is DecisionStatus.NO_FEASIBLE_ACTION:
        if any(item.feasible for item in result.evaluations):
            issues.append("no-feasible-action status contains feasible candidates")

    if result.status is DecisionStatus.ABSTAINED:
        if not result.evaluations:
            issues.append("abstention has no candidate evaluations")

    return tuple(issues)


def benchmark_decision_case(
    case_id: str,
    result: DecisionResult,
    *,
    expected_action_id: str | None,
    latency_ms: float,
    expected_status: DecisionStatus | None = None,
    expected_belief_revision: int | None = None,
    expected_world_revision: int | None = None,
) -> BenchmarkCaseResult:
    """Convert one decision outcome into the shared benchmark contract."""
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("case_id must be a non-empty string")

    if isinstance(latency_ms, bool) or not isinstance(latency_ms, (int, float)):
        raise ValueError("latency_ms must be a finite non-negative number")

    if not isfinite(latency_ms) or latency_ms < 0:
        raise ValueError("latency_ms must be a finite non-negative number")

    if expected_action_id is not None and (
        not isinstance(expected_action_id, str) or not expected_action_id.strip()
    ):
        raise ValueError("expected_action_id must be None or a non-empty string")

    if expected_status is not None and not isinstance(expected_status, DecisionStatus):
        raise TypeError("expected_status must be a DecisionStatus or None")

    if not isinstance(result, DecisionResult):
        raise TypeError("result must be a DecisionResult")

    issues = []

    if expected_belief_revision is not None:
        issues.extend(
            verify_decision_result(
                result,
                expected_belief_revision=expected_belief_revision,
                expected_world_revision=expected_world_revision,
            )
        )
    elif expected_world_revision is not None:
        raise ValueError("expected_belief_revision is required when checking world revision")

    if result.selected_action_id != expected_action_id:
        issues.append("selected action differs from benchmark expectation")

    if expected_status is not None and result.status is not expected_status:
        issues.append("decision status differs from benchmark expectation")

    return BenchmarkCaseResult(
        case_id=case_id,
        success=not issues,
        latency_ms=float(latency_ms),
        safety_violations=len(issues),
    )

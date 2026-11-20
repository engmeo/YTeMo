from types import SimpleNamespace

import pytest

from planning.governance import (
    ApprovalStatus, GovernanceRequest, evaluate_governance,
)
from planning.verification import verify_plan_structure
from planning.benchmark import BenchmarkCaseResult, summarize_benchmark
from planning.optimization import PlanningOption, pareto_frontier


def test_governance_approved_is_not_execution():
    result = evaluate_governance(GovernanceRequest("p1", 0.2))
    assert result.status is ApprovalStatus.APPROVED
    assert result.executable is False


def test_governance_requires_human_review_for_high_risk():
    result = evaluate_governance(GovernanceRequest("p2", 0.9))
    assert result.status is ApprovalStatus.PENDING
    assert "human_review_required" in result.reasons


def test_governance_consent_revocation_rejects():
    result = evaluate_governance(GovernanceRequest("p3", 0.1, consent_granted=False))
    assert result.status is ApprovalStatus.REJECTED


def test_governance_policy_denial_rejects():
    result = evaluate_governance(GovernanceRequest("p4", 0.1, policy_allowed=False))
    assert result.status is ApprovalStatus.REJECTED


def test_governance_missing_evidence_pending():
    result = evaluate_governance(GovernanceRequest("p5", 0.1, evidence_satisfied=False))
    assert result.status is ApprovalStatus.PENDING


def test_governance_invalid_threshold():
    with pytest.raises(ValueError):
        evaluate_governance(GovernanceRequest("p6", 0.1), mandatory_human_review_threshold=2)


def test_verify_valid_dag():
    plan = SimpleNamespace(steps=[
        SimpleNamespace(id="a", dependencies=()),
        SimpleNamespace(id="b", dependencies=("a",)),
    ])
    assert verify_plan_structure(plan).valid


def test_verify_missing_dependency():
    plan = SimpleNamespace(steps=[SimpleNamespace(id="a", dependencies=("missing",))])
    report = verify_plan_structure(plan)
    assert not report.valid
    assert "dependency_missing" in {f.code for f in report.findings}


def test_verify_cycle():
    plan = SimpleNamespace(steps=[
        SimpleNamespace(id="a", dependencies=("b",)),
        SimpleNamespace(id="b", dependencies=("a",)),
    ])
    report = verify_plan_structure(plan)
    assert "dependency_cycle" in {f.code for f in report.findings}


def test_verify_duplicate_ids():
    plan = SimpleNamespace(steps=[
        SimpleNamespace(id="a", dependencies=()),
        SimpleNamespace(id="a", dependencies=()),
    ])
    report = verify_plan_structure(plan)
    assert "duplicate_step_id" in {f.code for f in report.findings}


def test_verify_missing_steps():
    assert not verify_plan_structure(SimpleNamespace()).valid


def test_benchmark_summary():
    summary = summarize_benchmark([
        BenchmarkCaseResult("a", True, 10, 0),
        BenchmarkCaseResult("b", False, 20, 1),
    ])
    assert summary.case_count == 2
    assert summary.success_rate == 0.5
    assert summary.mean_latency_ms == 15
    assert summary.total_safety_violations == 1


def test_benchmark_empty_rejected():
    with pytest.raises(ValueError):
        summarize_benchmark([])


def test_benchmark_duplicate_case_rejected():
    item = BenchmarkCaseResult("a", True, 1)
    with pytest.raises(ValueError):
        summarize_benchmark([item, item])


def test_pareto_frontier_removes_dominated_option():
    options = [
        PlanningOption("best", 10, 5, 2, 0.1),
        PlanningOption("dominated", 8, 8, 3, 0.2),
        PlanningOption("tradeoff", 11, 9, 4, 0.3),
    ]
    ids = {item.option_id for item in pareto_frontier(options)}
    assert ids == {"best", "tradeoff"}


def test_pareto_frontier_keeps_equal_options():
    a = PlanningOption("a", 1, 1, 1, 0.1)
    b = PlanningOption("b", 1, 1, 1, 0.1)
    assert {x.option_id for x in pareto_frontier([a, b])} == {"a", "b"}


def test_option_rejects_invalid_risk():
    with pytest.raises(ValueError):
        PlanningOption("bad", 1, 1, 1, 1.5)

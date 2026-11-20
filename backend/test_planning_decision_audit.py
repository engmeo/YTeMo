import pytest

from planning.benchmark import summarize_benchmark
from planning.decision_engine import (
    DecisionCandidate,
    DecisionStatus,
    select_decision,
)
from planning.decision_audit import (
    benchmark_decision_case,
    verify_decision_result,
)
from planning.models import BeliefHypothesis, BeliefState, StateSnapshot


def make_belief(revision=4):
    snapshot = StateSnapshot(
        subject_id="audit-subject",
        domain="generic",
        revision=revision,
        as_of="2026-11-20T00:00:00+00:00",
        facts=(),
    )
    return BeliefState(
        snapshot=snapshot,
        hypotheses=(
            BeliefHypothesis("h1", "Hypothesis 1", 0.7),
            BeliefHypothesis("h2", "Hypothesis 2", 0.3),
        ),
    )


def make_candidate(action_id="a1", **kwargs):
    values = dict(
        action_id=action_id,
        description="Candidate",
        utilities={"h1": 10, "h2": 8},
        preconditions_satisfied=True,
    )
    values.update(kwargs)
    return DecisionCandidate(**values)


def make_selected():
    belief = make_belief()
    return select_decision(
        belief,
        (make_candidate(),),
    )


def test_valid_decision_trace_passes_audit():
    result = make_selected()
    assert verify_decision_result(
        result,
        expected_belief_revision=4,
    ) == ()


def test_stale_belief_revision_is_detected():
    result = make_selected()
    issues = verify_decision_result(
        result,
        expected_belief_revision=5,
    )
    assert "belief revision does not match the audited revision" in issues


def test_world_revision_mismatch_is_detected():
    result = make_selected()
    issues = verify_decision_result(
        result,
        expected_belief_revision=4,
        expected_world_revision=10,
    )
    assert "world revision does not match the audited revision" in issues


def test_selected_result_has_feasible_evaluation():
    result = make_selected()
    assert result.status is DecisionStatus.SELECTED
    assert result.selected_action_id == "a1"
    assert verify_decision_result(
        result,
        expected_belief_revision=4,
    ) == ()


def test_abstention_is_a_valid_auditable_outcome():
    result = select_decision(
        make_belief(),
        (
            make_candidate("a1"),
            make_candidate("a2"),
        ),
    )
    assert result.status is DecisionStatus.ABSTAINED
    assert result.selected_action_id is None
    assert verify_decision_result(
        result,
        expected_belief_revision=4,
    ) == ()


def test_benchmark_success_reuses_shared_contract():
    result = make_selected()
    benchmark = benchmark_decision_case(
        "decision-select",
        result,
        expected_action_id="a1",
        expected_status=DecisionStatus.SELECTED,
        expected_belief_revision=4,
        latency_ms=2.5,
    )
    assert benchmark.success
    assert benchmark.safety_violations == 0


def test_benchmark_detects_wrong_expected_action():
    result = make_selected()
    benchmark = benchmark_decision_case(
        "decision-wrong-action",
        result,
        expected_action_id="a2",
        latency_ms=1.0,
    )
    assert not benchmark.success
    assert benchmark.safety_violations == 1


def test_benchmark_detects_wrong_expected_status():
    result = make_selected()
    benchmark = benchmark_decision_case(
        "decision-wrong-status",
        result,
        expected_action_id="a1",
        expected_status=DecisionStatus.HUMAN_REVIEW,
        latency_ms=1.0,
    )
    assert not benchmark.success
    assert benchmark.safety_violations == 1


def test_benchmark_summary_uses_existing_engine():
    first = benchmark_decision_case(
        "case-1",
        make_selected(),
        expected_action_id="a1",
        latency_ms=2.0,
    )
    second = benchmark_decision_case(
        "case-2",
        make_selected(),
        expected_action_id="wrong",
        latency_ms=4.0,
    )

    summary = summarize_benchmark((first, second))
    assert summary.case_count == 2
    assert summary.success_rate == pytest.approx(0.5)
    assert summary.total_safety_violations == 1


def test_invalid_latency_is_rejected():
    with pytest.raises(ValueError):
        benchmark_decision_case(
            "bad-latency",
            make_selected(),
            expected_action_id="a1",
            latency_ms=-1,
        )


def test_world_revision_check_requires_belief_revision():
    with pytest.raises(ValueError):
        benchmark_decision_case(
            "bad-revision",
            make_selected(),
            expected_action_id="a1",
            expected_world_revision=2,
            latency_ms=1,
        )

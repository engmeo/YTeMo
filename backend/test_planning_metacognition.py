import pytest

from planning.metacognition import (
    FailureAnalysis,
    MetaCognitiveState,
    MetaDecisionStatus,
    MetaPolicy,
    OutcomeEvidence,
    ReasoningAction,
    ReasoningBudget,
    StrategyCandidate,
    StrategyProfile,
    analyze_outcome,
    assess_reasoning_budget,
    record_verified_outcome,
    select_strategy,
)


def evidence(
    evidence_id="e1",
    strategy_id="alpha",
    observed=8.0,
    expected=10.0,
    verified=True,
    **kwargs,
):
    return OutcomeEvidence(
        evidence_id=evidence_id,
        strategy_id=strategy_id,
        expected_utility=expected,
        observed_utility=observed,
        verified=verified,
        **kwargs,
    )


def test_unverified_evidence_does_not_change_state():
    state = MetaCognitiveState()
    result = record_verified_outcome(
        state, evidence(verified=False)
    )
    assert not result.accepted
    assert result.state == state
    assert result.reason == "evidence_not_verified"


def test_safety_violation_evidence_is_rejected():
    state = MetaCognitiveState()
    result = record_verified_outcome(
        state, evidence(safety_violation=True)
    )
    assert not result.accepted
    assert result.state == state
    assert result.reason == "safety_violation"


def test_verified_evidence_creates_profile():
    result = record_verified_outcome(
        MetaCognitiveState(), evidence()
    )
    assert result.accepted
    profile = result.state.get_profile("alpha")
    assert profile is not None
    assert profile.trials == 1
    assert profile.verified_trials == 1
    assert profile.mean_reward == 8.0


def test_online_mean_and_variance_update():
    state = MetaCognitiveState()
    state = record_verified_outcome(
        state, evidence("e1", observed=2.0)
    ).state
    state = record_verified_outcome(
        state, evidence("e2", observed=4.0)
    ).state
    profile = state.get_profile("alpha")
    assert profile.mean_reward == pytest.approx(3.0)
    assert profile.reward_variance == pytest.approx(2.0)


def test_duplicate_last_evidence_is_rejected():
    state = record_verified_outcome(
        MetaCognitiveState(), evidence("same")
    ).state
    result = record_verified_outcome(
        state, evidence("same")
    )
    assert not result.accepted
    assert result.reason == "duplicate_evidence"


def test_state_keeps_compact_profiles_not_event_history():
    state = MetaCognitiveState()
    for index in range(20):
        state = record_verified_outcome(
            state,
            evidence(f"e{index}", observed=float(index)),
        ).state
    profile = state.get_profile("alpha")
    assert profile.trials == 20
    assert not hasattr(state, "history")
    assert not hasattr(profile, "events")


def test_failure_analysis_computes_expected_observed_delta():
    result = analyze_outcome(
        evidence(observed=6.0, expected=10.0, failure_class="timeout")
    )
    assert result.utility_delta == -4.0
    assert result.failure_class == "timeout"
    assert result.evidence_verified


def test_strategy_selection_uses_verified_profile():
    state = MetaCognitiveState()
    state = record_verified_outcome(
        state, evidence("e1", "alpha", observed=9.0)
    ).state
    state = record_verified_outcome(
        state, evidence("e2", "beta", observed=2.0)
    ).state

    result = select_strategy(
        [StrategyCandidate("alpha"), StrategyCandidate("beta")],
        state,
        MetaPolicy(exploration_coefficient=0.0),
    )
    assert result.status == MetaDecisionStatus.SELECTED
    assert result.selected_strategy_id == "alpha"


def test_cold_start_uses_bounded_exploration():
    result = select_strategy(
        [StrategyCandidate("new")],
        MetaCognitiveState(),
    )
    assert result.selected_strategy_id == "new"
    assessment = result.assessments[0]
    assert "bounded_cold_start_exploration" in assessment.reasons


def test_cold_start_can_be_disabled():
    result = select_strategy(
        [StrategyCandidate("new")],
        MetaCognitiveState(),
        MetaPolicy(allow_bounded_exploration=False),
    )
    assert result.status == MetaDecisionStatus.NO_FEASIBLE_STRATEGY
    assert result.selected_strategy_id is None


def test_safety_ineligible_candidate_is_never_selected():
    result = select_strategy(
        [
            StrategyCandidate("unsafe", safety_eligible=False),
            StrategyCandidate("safe"),
        ],
        MetaCognitiveState(),
    )
    assert result.selected_strategy_id == "safe"
    unsafe = next(x for x in result.assessments if x.strategy_id == "unsafe")
    assert not unsafe.eligible


def test_resource_and_latency_constraints_are_enforced():
    result = select_strategy(
        [
            StrategyCandidate("expensive", estimated_cost=20),
            StrategyCandidate("slow", estimated_latency_ms=5000),
        ],
        MetaCognitiveState(),
        MetaPolicy(
            max_resource_cost=10,
            max_latency_ms=1000,
        ),
    )
    assert result.status == MetaDecisionStatus.NO_FEASIBLE_STRATEGY
    assert all(not item.eligible for item in result.assessments)


def test_human_approval_candidate_is_not_auto_selected():
    result = select_strategy(
        [StrategyCandidate("needs_review", requires_human_approval=True)],
        MetaCognitiveState(),
    )
    assert result.status == MetaDecisionStatus.HUMAN_REVIEW
    assert result.selected_strategy_id is None


def test_introspection_trace_records_policy_and_reasons():
    result = select_strategy(
        [StrategyCandidate("alpha")],
        MetaCognitiveState(revision=7),
        MetaPolicy(policy_version="test-policy-v2"),
    )
    assert result.trace.policy_version == "test-policy-v2"
    assert result.trace.state_revision == 7
    assert result.trace.selected_strategy_id == "alpha"
    assert result.trace.assessments == result.assessments


def test_ties_are_deterministic():
    result = select_strategy(
        [StrategyCandidate("zeta"), StrategyCandidate("alpha")],
        MetaCognitiveState(),
    )
    assert result.selected_strategy_id == "alpha"


def test_no_candidates_returns_no_feasible_strategy():
    result = select_strategy([], MetaCognitiveState())
    assert result.status == MetaDecisionStatus.NO_FEASIBLE_STRATEGY
    assert result.selected_strategy_id is None


def test_reasoning_continues_when_value_and_budget_allow():
    result = assess_reasoning_budget(
        ReasoningBudget(
            max_iterations=5,
            used_iterations=2,
            max_compute_units=10,
            used_compute_units=3,
            max_latency_ms=1000,
            used_latency_ms=200,
        ),
        expected_value_of_more_reasoning=1.0,
        estimated_next_compute_units=2,
        estimated_next_latency_ms=100,
    )
    assert result.action == ReasoningAction.CONTINUE_SEARCH
    assert result.remaining_iterations == 3


def test_reasoning_stops_when_iteration_budget_exhausted():
    result = assess_reasoning_budget(
        ReasoningBudget(max_iterations=2, used_iterations=2),
        expected_value_of_more_reasoning=10,
    )
    assert result.action == ReasoningAction.STOP


def test_reasoning_stops_when_resource_budget_insufficient():
    result = assess_reasoning_budget(
        ReasoningBudget(
            max_iterations=5,
            max_compute_units=3,
            used_compute_units=2,
            max_latency_ms=100,
        ),
        expected_value_of_more_reasoning=10,
        estimated_next_compute_units=2,
    )
    assert result.action == ReasoningAction.STOP


def test_reasoning_requests_human_review_when_required():
    result = assess_reasoning_budget(
        ReasoningBudget(max_iterations=5),
        expected_value_of_more_reasoning=10,
        requires_human_review=True,
    )
    assert result.action == ReasoningAction.HUMAN_REVIEW


def test_reasoning_evaluates_when_more_search_has_no_value():
    result = assess_reasoning_budget(
        ReasoningBudget(max_iterations=5),
        expected_value_of_more_reasoning=0,
    )
    assert result.action == ReasoningAction.EVALUATE


def test_invalid_negative_evidence_cost_is_rejected():
    with pytest.raises(ValueError):
        evidence(resource_cost=-1)


def test_invalid_duplicate_strategy_candidates_are_rejected():
    with pytest.raises(ValueError):
        select_strategy(
            [StrategyCandidate("same"), StrategyCandidate("same")],
            MetaCognitiveState(),
        )


def test_policy_is_immutable():
    policy = MetaPolicy()
    with pytest.raises((AttributeError, TypeError)):
        policy.max_resource_cost = 999


def test_profile_tracks_failures_without_storing_history():
    state = MetaCognitiveState()
    state = record_verified_outcome(
        state,
        evidence("e1", failure_class="timeout"),
    ).state
    profile = state.get_profile("alpha")
    assert profile.failures == 1
    assert profile.trials == 1
    assert not hasattr(profile, "history")

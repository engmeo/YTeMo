import pytest

from planning.models import (
    BeliefHypothesis,
    BeliefState,
    StateSnapshot,
)
from planning.decision_engine import (
    DecisionCandidate,
    DecisionPolicy,
    evaluate_candidate,
    evaluate_candidates,
)


def make_belief(probabilities=(0.7, 0.3)):
    snapshot = StateSnapshot(
        subject_id="test-subject",
        domain="generic",
        revision=4,
        as_of="2026-11-20T00:00:00+00:00",
        facts=(),
    )
    hypotheses = tuple(
        BeliefHypothesis(f"h{i}", f"Hypothesis {i}", p)
        for i, p in enumerate(probabilities)
    )
    return BeliefState(snapshot=snapshot, hypotheses=hypotheses)


def test_expected_utility_uses_normalized_beliefs():
    belief = make_belief((0.7, 0.3))
    candidate = DecisionCandidate(
        "a1", "Action 1", {"h0": 10, "h1": -10},
        preconditions_satisfied=True,
    )
    result = evaluate_candidate(belief, candidate)

    assert result.expected_utility == pytest.approx(4.0)
    assert result.score == pytest.approx(4.0)
    assert result.feasible


def test_candidate_penalties_are_explicit():
    belief = make_belief()
    candidate = DecisionCandidate(
        "a1", "Action 1", {"h0": 10, "h1": 10},
        cost=2, risk=0.2, uncertainty=0.1,
        preconditions_satisfied=True,
    )
    policy = DecisionPolicy(
        cost_weight=2, risk_weight=3, uncertainty_weight=4
    )
    result = evaluate_candidate(belief, candidate, policy)

    assert result.expected_utility == pytest.approx(10)
    assert result.cost_penalty == pytest.approx(4)
    assert result.risk_penalty == pytest.approx(0.6)
    assert result.uncertainty_penalty == pytest.approx(0.4)
    assert result.score == pytest.approx(5)


def test_unknown_preconditions_are_not_assumed_safe():
    result = evaluate_candidate(
        make_belief(),
        DecisionCandidate("a1", "Action", {"h0": 1, "h1": 1}),
    )
    assert not result.feasible
    assert "preconditions are unknown" in result.reasons


def test_policy_blocks_risk_and_uncertainty_excess():
    result = evaluate_candidate(
        make_belief(),
        DecisionCandidate(
            "a1", "Action", {"h0": 1, "h1": 1},
            risk=0.8, uncertainty=0.7,
            preconditions_satisfied=True,
        ),
        DecisionPolicy(max_risk=0.5, max_uncertainty=0.5),
    )
    assert not result.feasible
    assert len(result.reasons) == 2


def test_belief_concentration_threshold():
    belief = make_belief((0.5, 0.5))
    candidate = DecisionCandidate(
        "a1", "Action", {"h0": 1, "h1": 1},
        preconditions_satisfied=True,
    )
    result = evaluate_candidate(
        belief, candidate, DecisionPolicy(min_belief_confidence=0.5)
    )
    assert not result.feasible
    assert "belief concentration is below policy minimum" in result.reasons


def test_utility_hypothesis_mismatch_rejected():
    with pytest.raises(ValueError):
        evaluate_candidate(
            make_belief(),
            DecisionCandidate("a1", "Action", {"h0": 1}),
        )


def test_empty_belief_rejected():
    snapshot = StateSnapshot(
        subject_id="s", domain="generic", revision=0,
        as_of="2026-11-20T00:00:00+00:00", facts=(),
    )
    belief = BeliefState(snapshot=snapshot)
    candidate = DecisionCandidate("a1", "Action", {"h0": 1})

    with pytest.raises(ValueError):
        evaluate_candidate(belief, candidate)


def test_candidate_collection_rejects_duplicate_ids():
    candidate = DecisionCandidate(
        "a1", "Action", {"h0": 1, "h1": 1},
        preconditions_satisfied=True,
    )
    with pytest.raises(ValueError):
        evaluate_candidates(make_belief(), (candidate, candidate))


def test_candidate_collection_evaluates_all():
    belief = make_belief()
    candidates = (
        DecisionCandidate("a1", "First", {"h0": 10, "h1": 0}, preconditions_satisfied=True),
        DecisionCandidate("a2", "Second", {"h0": 0, "h1": 10}, preconditions_satisfied=True),
    )
    results = evaluate_candidates(belief, candidates)

    assert len(results) == 2
    assert results[0].expected_utility == pytest.approx(7)
    assert results[1].expected_utility == pytest.approx(3)

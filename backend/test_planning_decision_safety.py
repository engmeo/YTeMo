import pytest

from planning.decision_engine import (
    DecisionCandidate,
    DecisionPolicy,
    DecisionStatus,
    select_decision,
)
from planning.models import BeliefHypothesis, BeliefState, StateSnapshot


def make_belief():
    snapshot = StateSnapshot(
        subject_id="s",
        domain="generic",
        revision=1,
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


def make_candidate(**kwargs):
    values = dict(
        action_id="a1",
        description="Safe candidate",
        utilities={"h1": 10, "h2": 8},
        preconditions_satisfied=True,
    )
    values.update(kwargs)
    return DecisionCandidate(**values)


def test_high_uncertainty_triggers_human_review():
    result = select_decision(
        make_belief(),
        (make_candidate(uncertainty=0.8),),
        DecisionPolicy(human_review_uncertainty_threshold=0.7),
    )
    assert result.status is DecisionStatus.HUMAN_REVIEW
    assert result.selected_action_id == "a1"


def test_uncertainty_below_review_threshold_keeps_selection():
    result = select_decision(
        make_belief(),
        (make_candidate(uncertainty=0.6),),
        DecisionPolicy(human_review_uncertainty_threshold=0.7),
    )
    assert result.status is DecisionStatus.SELECTED


def test_default_uncertainty_threshold_preserves_previous_behavior():
    result = select_decision(
        make_belief(),
        (make_candidate(uncertainty=0.8),),
    )
    assert result.status is DecisionStatus.SELECTED


def test_uncertainty_threshold_is_validated():
    with pytest.raises(ValueError):
        DecisionPolicy(human_review_uncertainty_threshold=1.1)


def test_no_feasible_candidate_still_fails_closed():
    result = select_decision(
        make_belief(),
        (make_candidate(preconditions_satisfied=False),),
    )
    assert result.status is DecisionStatus.NO_FEASIBLE_ACTION
    assert result.selected_action_id is None

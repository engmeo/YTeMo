import pytest

from planning.decision_engine import (
    DecisionCandidate,
    DecisionPolicy,
    DecisionStatus,
    select_decision,
)
from planning.world_model import WorldPrediction, WorldState
from test_planning_decision_evaluation import make_belief


def candidates():
    return (
        DecisionCandidate(
            "a1", "First", {"h0": 10, "h1": 0},
            preconditions_satisfied=True,
        ),
        DecisionCandidate(
            "a2", "Second", {"h0": 0, "h1": 10},
            preconditions_satisfied=True,
        ),
    )


def make_prediction(belief, action, revision=4, applicable=True, uncertainty=0.1):
    state = WorldState.from_snapshot(belief.snapshot, values={})
    return WorldPrediction(
        rule_id=f"rule-{action}",
        rule_version=1,
        action=action,
        source_revision=revision,
        applicable=applicable,
        predicted_state=state,
        confidence=1.0 - uncertainty,
        uncertainty=uncertainty,
        changed_keys=(),
        reasons=(),
    )


def test_selects_highest_scoring_feasible_candidate():
    result = select_decision(make_belief(), candidates())

    assert result.status == DecisionStatus.SELECTED
    assert result.selected_action_id == "a1"
    assert result.trace.selected_action_id == "a1"


def test_tied_candidates_cause_abstention():
    belief = make_belief()
    options = (
        DecisionCandidate("a1", "First", {"h0": 5, "h1": 5},
                           preconditions_satisfied=True),
        DecisionCandidate("a2", "Second", {"h0": 5, "h1": 5},
                           preconditions_satisfied=True),
    )

    result = select_decision(belief, options)

    assert result.status == DecisionStatus.ABSTAINED
    assert result.selected_action_id is None


def test_human_approval_candidate_is_not_auto_selected():
    options = (
        DecisionCandidate(
            "a1", "Sensitive action", {"h0": 10, "h1": 10},
            preconditions_satisfied=True,
            requires_human_approval=True,
        ),
    )

    result = select_decision(make_belief(), options)

    assert result.status == DecisionStatus.HUMAN_REVIEW
    assert result.selected_action_id == "a1"


def test_risk_threshold_routes_to_human_review():
    options = (
        DecisionCandidate(
            "a1", "Risky action", {"h0": 10, "h1": 10},
            risk=0.7,
            preconditions_satisfied=True,
        ),
    )

    result = select_decision(
        make_belief(),
        options,
        DecisionPolicy(human_review_risk_threshold=0.7),
    )

    assert result.status == DecisionStatus.HUMAN_REVIEW


def test_no_feasible_candidate_returns_no_feasible_action():
    options = (
        DecisionCandidate("a1", "Blocked", {"h0": 10, "h1": 10}),
    )

    result = select_decision(make_belief(), options)

    assert result.status == DecisionStatus.NO_FEASIBLE_ACTION
    assert result.selected_action_id is None


def test_non_applicable_world_prediction_blocks_candidate():
    belief = make_belief()
    options = (
        DecisionCandidate(
            "a1", "Action", {"h0": 10, "h1": 10},
            preconditions_satisfied=True,
        ),
    )

    result = select_decision(
        belief,
        options,
        world_predictions=(make_prediction(belief, "a1", applicable=False),),
        world_revision=4,
    )

    assert result.status == DecisionStatus.NO_FEASIBLE_ACTION
    assert "world prediction is not applicable" in result.evaluations[0].reasons


def test_stale_world_prediction_blocks_candidate():
    belief = make_belief()
    options = (
        DecisionCandidate(
            "a1", "Action", {"h0": 10, "h1": 10},
            preconditions_satisfied=True,
        ),
    )

    result = select_decision(
        belief,
        options,
        world_predictions=(make_prediction(belief, "a1", revision=3),),
        world_revision=4,
    )

    assert result.status == DecisionStatus.NO_FEASIBLE_ACTION
    assert "world prediction is stale" in result.evaluations[0].reasons


def test_missing_world_prediction_blocks_candidate():
    options = (
        DecisionCandidate(
            "a1", "Action", {"h0": 10, "h1": 10},
            preconditions_satisfied=True,
        ),
    )

    result = select_decision(
        make_belief(), options, world_predictions=(), world_revision=4
    )
    assert result.status == DecisionStatus.SELECTED

    result = select_decision(
        make_belief(),
        options,
        world_predictions=(
            make_prediction(make_belief(), "other-action"),
        ),
        world_revision=4,
    )
    assert result.status == DecisionStatus.NO_FEASIBLE_ACTION
    assert "world prediction is missing" in result.evaluations[0].reasons


def test_tie_tolerance_must_be_non_negative():
    with pytest.raises(ValueError):
        select_decision(make_belief(), candidates(), tie_tolerance=-1)

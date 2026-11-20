import pytest

from planning.decision_engine import (
    DecisionCandidate,
    DecisionEvaluation,
    DecisionPolicy,
    DecisionResult,
    DecisionStatus,
    DecisionTrace,
)


def test_candidate_immutability():
    source = {"h1": 10, "h2": -2}
    item = DecisionCandidate("a1", "candidate", source, risk=0.2)
    source["h1"] = 999
    assert item.utilities["h1"] == 10
    with pytest.raises(TypeError):
        item.utilities["h1"] = 3


@pytest.mark.parametrize("kwargs", [
    {"cost": -1},
    {"risk": 1.1},
    {"uncertainty": -0.1},
    {"utilities": {}},
    {"utilities": {"h1": float("nan")}},
])
def test_candidate_rejects_invalid_values(kwargs):
    values = {"utilities": {"h1": 1}}
    values.update(kwargs)
    with pytest.raises(ValueError):
        DecisionCandidate("a1", "candidate", **values)


def test_policy_validation():
    assert DecisionPolicy().max_risk == 1.0
    with pytest.raises(ValueError):
        DecisionPolicy(risk_weight=-1)
    with pytest.raises(ValueError):
        DecisionPolicy(max_uncertainty=1.2)


def test_trace_requires_candidate_for_selected_or_review():
    trace = DecisionTrace(DecisionStatus.HUMAN_REVIEW, 2, 3, "a1", "risk threshold")
    assert trace.selected_action_id == "a1"
    with pytest.raises(ValueError):
        DecisionTrace(DecisionStatus.SELECTED, 2, None, None, "missing candidate")
    with pytest.raises(ValueError):
        DecisionTrace(DecisionStatus.ABSTAINED, 2, None, "a1", "must abstain")


def test_result_consistency():
    evaluation = DecisionEvaluation("a1", 5, 0, 0, 0, 5, True)
    trace = DecisionTrace(DecisionStatus.SELECTED, 1, 1, "a1", "highest score")
    result = DecisionResult(DecisionStatus.SELECTED, "a1", (evaluation,), trace)
    assert result.selected_action_id == "a1"

    with pytest.raises(ValueError):
        DecisionResult(DecisionStatus.SELECTED, "a2", (evaluation,), trace)


def test_abstention_without_selected_action():
    trace = DecisionTrace(DecisionStatus.ABSTAINED, 4, None, None, "insufficient evidence")
    result = DecisionResult(DecisionStatus.ABSTAINED, None, (), trace)
    assert result.status is DecisionStatus.ABSTAINED

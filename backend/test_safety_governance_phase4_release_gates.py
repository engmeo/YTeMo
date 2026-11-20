"""Phase 4 release gates for safety, governance, and independent review contracts."""
import math
import pytest

from planning.risk import RiskItem, assess_risks
from planning.governance import (
    ApprovalStatus,
    GovernanceRequest,
    evaluate_governance,
)
from planning.decision_engine import (
    DecisionCandidate,
    DecisionPolicy,
    DecisionStatus,
    select_decision,
)
from planning.decision_audit import verify_decision_result
from planning.models import BeliefHypothesis, BeliefState, StateSnapshot


def _belief(revision=7):
    snapshot = StateSnapshot(
        subject_id="phase4-subject",
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


def _candidate(**overrides):
    values = dict(
        action_id="proposal-1",
        description="Proposed action",
        utilities={"h1": 8.0, "h2": 6.0},
        preconditions_satisfied=True,
    )
    values.update(overrides)
    return DecisionCandidate(**values)


def test_risk_assessment_preserves_aggregate_expected_loss():
    assessment = assess_risks((
        RiskItem("r1", probability=0.8, impact=0.9),
        RiskItem("r2", probability=0.7, impact=0.8),
    ), max_expected_loss=0.5)
    assert assessment.total_expected_loss == pytest.approx(1.28)
    assert assessment.highest_single_risk == pytest.approx(0.72)
    assert assessment.within_threshold is False
    assert len(assessment.items) == 2


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), -0.01, 1.01])
def test_risk_inputs_reject_invalid_probability_or_impact(value):
    with pytest.raises(ValueError):
        RiskItem("invalid", probability=value, impact=0.5)


def test_risk_assessment_rejects_duplicate_ids_and_invalid_threshold():
    item = RiskItem("same", 0.2, 0.3)
    with pytest.raises(ValueError):
        assess_risks((item, item))
    with pytest.raises(ValueError):
        assess_risks((item,), max_expected_loss=float("nan"))


def test_governance_approval_never_authorizes_execution():
    result = evaluate_governance(GovernanceRequest("plan-safe", 0.2))
    assert result.status is ApprovalStatus.APPROVED
    assert result.executable is False


def test_governance_fails_closed_for_revoked_consent_or_policy_denial():
    consent = evaluate_governance(
        GovernanceRequest("plan-consent", 0.1, consent_granted=False)
    )
    policy = evaluate_governance(
        GovernanceRequest("plan-policy", 0.1, policy_allowed=False)
    )
    assert consent.status is ApprovalStatus.REJECTED
    assert "consent_missing_or_revoked" in consent.reasons
    assert policy.status is ApprovalStatus.REJECTED
    assert "domain_policy_denied" in policy.reasons
    assert consent.executable is False
    assert policy.executable is False


def test_governance_escalates_high_risk_and_missing_evidence():
    high_risk = evaluate_governance(GovernanceRequest("plan-risk", 0.9))
    missing_evidence = evaluate_governance(
        GovernanceRequest("plan-evidence", 0.1, evidence_satisfied=False)
    )
    assert high_risk.status is ApprovalStatus.PENDING
    assert "human_review_required" in high_risk.reasons
    assert missing_evidence.status is ApprovalStatus.PENDING
    assert "evidence_requirements_not_met" in missing_evidence.reasons


def test_decision_audit_detects_stale_belief_and_world_revisions():
    result = select_decision(_belief(), (_candidate(),))
    assert verify_decision_result(
        result, expected_belief_revision=7
    ) == ()
    stale = verify_decision_result(
        result, expected_belief_revision=8
    )
    world_mismatch = verify_decision_result(
        result, expected_belief_revision=7, expected_world_revision=99
    )
    assert "belief revision does not match the audited revision" in stale
    assert "world revision does not match the audited revision" in world_mismatch


def test_abstention_remains_a_valid_auditable_decision():
    result = select_decision(
        _belief(),
        (
            _candidate(action_id="a1"),
            _candidate(action_id="a2"),
        ),
    )
    assert result.status is DecisionStatus.ABSTAINED
    assert result.selected_action_id is None
    assert verify_decision_result(
        result, expected_belief_revision=7
    ) == ()


def test_uncertainty_escalation_and_infeasible_candidate_are_distinct():
    reviewed = select_decision(
        _belief(),
        (_candidate(uncertainty=0.85),),
        DecisionPolicy(human_review_uncertainty_threshold=0.7),
    )
    infeasible = select_decision(
        _belief(),
        (_candidate(preconditions_satisfied=False),),
    )
    assert reviewed.status is DecisionStatus.HUMAN_REVIEW
    assert infeasible.status is DecisionStatus.NO_FEASIBLE_ACTION
    assert infeasible.selected_action_id is None
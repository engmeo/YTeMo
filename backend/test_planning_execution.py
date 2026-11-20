import pytest

from planning.execution import (
    ExecutionFeedback,
    ExecutionStepStatus,
    RecoveryAction,
    RecoveryPolicy,
    initialize_execution,
    mark_step_started,
    record_step_success,
    record_step_failure,
    record_execution_feedback,
    evaluate_recovery,
    record_recovery_recommendation,
)
from planning.models import (
    Goal, Plan, PlanStep, StateSnapshot, StepRisk,
)
from planning.world_model import PredictionEvaluation


def make_plan(risk=StepRisk.LOW, approval=False, two_steps=False):
    snapshot = StateSnapshot(
        subject_id="execution-test",
        domain="generic",
        revision=3,
        as_of="2026-11-20T00:00:00+00:00",
        facts=(),
    )
    goal = Goal(
        goal_id="goal-1",
        description="Test goal",
        domain="generic",
    )
    steps = [
        PlanStep(
            step_id="step-1",
            action="action-1",
            description="First step",
            risk=risk,
            requires_human_approval=approval,
        )
    ]
    if two_steps:
        steps.append(
            PlanStep(
                step_id="step-2",
                action="action-2",
                description="Second step",
                depends_on=("step-1",),
            )
        )
    return Plan.create(goal, snapshot, steps)


def test_initialize_execution_creates_pending_records():
    plan = make_plan(two_steps=True)
    state = initialize_execution(plan, 10)
    assert state.plan_id == plan.plan_id
    assert state.world_revision == 10
    assert all(x.status is ExecutionStepStatus.PENDING for x in state.records)


def test_start_and_success_are_recorded():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    state = mark_step_started(plan, state, "step-1")
    assert state.record("step-1").status is ExecutionStepStatus.RUNNING
    state = record_step_success(
        plan, state, "step-1",
        observed_effects={"done": True},
    )
    assert state.record("step-1").status is ExecutionStepStatus.SUCCEEDED
    assert state.record("step-1").observed_effects["done"] is True


def test_dependency_must_succeed_before_dependent_step_starts():
    plan = make_plan(two_steps=True)
    state = initialize_execution(plan, 10)
    with pytest.raises(ValueError):
        mark_step_started(plan, state, "step-2")


def test_dependency_can_start_after_parent_succeeds():
    plan = make_plan(two_steps=True)
    state = initialize_execution(plan, 10)
    state = mark_step_started(plan, state, "step-1")
    state = record_step_success(plan, state, "step-1")
    state = mark_step_started(plan, state, "step-2")
    assert state.record("step-2").status is ExecutionStepStatus.RUNNING


def test_human_approval_is_required_before_start():
    plan = make_plan(approval=True)
    state = initialize_execution(plan, 10)
    with pytest.raises(PermissionError):
        mark_step_started(plan, state, "step-1")


def test_explicit_approval_allows_start():
    plan = make_plan(approval=True)
    state = initialize_execution(plan, 10)
    state = mark_step_started(
        plan, state, "step-1", approval_granted=True
    )
    assert state.record("step-1").status is ExecutionStepStatus.RUNNING


def test_failed_step_records_error():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    state = mark_step_started(plan, state, "step-1")
    state = record_step_failure(plan, state, "step-1", "external failure")
    assert state.record("step-1").status is ExecutionStepStatus.FAILED
    assert state.record("step-1").error == "external failure"


def test_retry_recommended_when_budget_remains():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    state = mark_step_started(plan, state, "step-1")
    state = record_step_failure(plan, state, "step-1", "temporary")
    decision = evaluate_recovery(plan, state, "step-1")
    assert decision.action is RecoveryAction.RETRY


def test_replanning_recommended_after_retry_budget_exhausted():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    for _ in range(3):
        state = mark_step_started(plan, state, "step-1")
        state = record_step_failure(plan, state, "step-1", "failure")
    decision = evaluate_recovery(plan, state, "step-1")
    assert decision.action is RecoveryAction.REPLAN
    assert decision.requires_new_plan


def test_disabled_replanning_causes_pause_after_retries():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    for _ in range(3):
        state = mark_step_started(plan, state, "step-1")
        state = record_step_failure(plan, state, "step-1", "failure")
    decision = evaluate_recovery(
        plan, state, "step-1",
        policy=RecoveryPolicy(allow_replanning=False),
    )
    assert decision.action is RecoveryAction.PAUSE


def test_high_risk_step_requires_human_review():
    plan = make_plan(risk=StepRisk.HIGH)
    state = initialize_execution(plan, 10)
    state = mark_step_started(plan, state, "step-1")
    state = record_step_failure(plan, state, "step-1", "failure")
    decision = evaluate_recovery(plan, state, "step-1")
    assert decision.action is RecoveryAction.HUMAN_REVIEW


def test_stale_world_revision_triggers_replanning():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    state = mark_step_started(plan, state, "step-1")
    state = record_step_failure(plan, state, "step-1", "failure")
    decision = evaluate_recovery(
        plan, state, "step-1", current_world_revision=11
    )
    assert decision.action is RecoveryAction.REPLAN


def test_successful_step_recommends_continue():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    state = mark_step_started(plan, state, "step-1")
    state = record_step_success(plan, state, "step-1")
    decision = evaluate_recovery(plan, state, "step-1")
    assert decision.action is RecoveryAction.CONTINUE


def test_prediction_deviation_triggers_replanning():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    state = mark_step_started(plan, state, "step-1")
    state = record_step_success(plan, state, "step-1")

    evaluation = PredictionEvaluation(
        rule_id="rule-1",
        compared_keys=("position",),
        matched_keys=(),
        mismatched_keys=("position",),
        missing_keys=(),
        accuracy=0.0,
    )
    feedback = ExecutionFeedback(
        step_id="step-1",
        prediction_evaluation=evaluation,
    )
    decision = evaluate_recovery(
        plan, state, "step-1", feedback=feedback
    )
    assert decision.deviation_detected
    assert decision.action is RecoveryAction.REPLAN


def test_deviation_can_force_pause():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    state = mark_step_started(plan, state, "step-1")
    state = record_step_success(plan, state, "step-1")

    evaluation = PredictionEvaluation(
        rule_id="rule-1",
        compared_keys=("x",),
        matched_keys=(),
        mismatched_keys=("x",),
        missing_keys=(),
        accuracy=0.0,
    )
    decision = evaluate_recovery(
        plan, state, "step-1",
        feedback=ExecutionFeedback("step-1", evaluation),
        policy=RecoveryPolicy(pause_on_deviation=True),
    )
    assert decision.action is RecoveryAction.PAUSE


def test_feedback_is_appended_to_audit_trace():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    state = mark_step_started(plan, state, "step-1")
    feedback = ExecutionFeedback(
        "step-1",
        observed_effects={"temperature": 20},
        evidence_refs=("sensor:1",),
    )
    state = record_execution_feedback(plan, state, feedback)
    assert state.events[-1].details["deviation_detected"] is False
    assert state.record("step-1").evidence_refs == ("sensor:1",)


def test_recovery_recommendation_is_audited():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    state = mark_step_started(plan, state, "step-1")
    state = record_step_failure(plan, state, "step-1", "failure")
    decision = evaluate_recovery(plan, state, "step-1")
    state = record_recovery_recommendation(state, decision)
    assert state.events[-1].details["action"] == "retry"


def test_stale_plan_version_is_rejected():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    changed_plan = Plan(
        plan_id=plan.plan_id,
        goal_id=plan.goal_id,
        domain=plan.domain,
        state_revision=plan.state_revision,
        steps=plan.steps,
        created_at=plan.created_at,
        version=plan.version + 1,
    )
    with pytest.raises(ValueError):
        mark_step_started(changed_plan, state, "step-1")


def test_success_cannot_be_recorded_without_start():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    with pytest.raises(ValueError):
        record_step_success(plan, state, "step-1")


def test_invalid_retry_budget_is_rejected():
    with pytest.raises(ValueError):
        RecoveryPolicy(max_retries=-1)


def test_unknown_step_is_rejected():
    plan = make_plan()
    state = initialize_execution(plan, 10)
    with pytest.raises(KeyError):
        mark_step_started(plan, state, "missing")

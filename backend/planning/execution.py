"""Domain-neutral execution monitoring and adaptive recovery.

This module records execution state and recommends recovery actions.
It does not execute tools, dispatch actions, or persist application state.
AgentCore remains responsible for durable task lifecycle and execution.
"""
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from .models import Plan, PlanStep, StepRisk
from .world_model import PredictionEvaluation


class ExecutionStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    HUMAN_REVIEW = "human_review"
    SKIPPED = "skipped"


class ExecutionEventType(str, Enum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    FEEDBACK_RECEIVED = "feedback_received"
    RECOVERY_RECOMMENDED = "recovery_recommended"


class RecoveryAction(str, Enum):
    CONTINUE = "continue"
    RETRY = "retry"
    REPLAN = "replan"
    PAUSE = "pause"
    HUMAN_REVIEW = "human_review"
    ABORT = "abort"


@dataclass(frozen=True)
class ExecutionStepRecord:
    step_id: str
    status: ExecutionStepStatus = ExecutionStepStatus.PENDING
    attempts: int = 0
    error: str | None = None
    observed_effects: Mapping[str, object] | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.step_id, str) or not self.step_id.strip():
            raise ValueError("step_id must be non-empty")
        if not isinstance(self.status, ExecutionStepStatus):
            raise TypeError("status must be ExecutionStepStatus")
        if isinstance(self.attempts, bool) or not isinstance(self.attempts, int) or self.attempts < 0:
            raise ValueError("attempts must be a non-negative integer")
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError("error must be a string or None")
        object.__setattr__(
            self, "observed_effects",
            MappingProxyType(dict(self.observed_effects or {})),
        )
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))


@dataclass(frozen=True)
class ExecutionEvent:
    sequence: int
    event_type: ExecutionEventType
    step_id: str
    timestamp: str | None = None
    details: Mapping[str, object] | None = None

    def __post_init__(self):
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise ValueError("sequence must be a positive integer")
        if not isinstance(self.event_type, ExecutionEventType):
            raise TypeError("event_type must be ExecutionEventType")
        if not isinstance(self.step_id, str) or not self.step_id.strip():
            raise ValueError("step_id must be non-empty")
        object.__setattr__(
            self, "details",
            MappingProxyType(dict(self.details or {})),
        )


@dataclass(frozen=True)
class ExecutionSnapshot:
    plan_id: str
    plan_version: int
    world_revision: int
    records: tuple[ExecutionStepRecord, ...]
    events: tuple[ExecutionEvent, ...] = ()

    def __post_init__(self):
        if not isinstance(self.plan_id, str) or not self.plan_id.strip():
            raise ValueError("plan_id must be non-empty")
        for name, value in (
            ("plan_version", self.plan_version),
            ("world_revision", self.world_revision),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        records = tuple(self.records)
        if len({item.step_id for item in records}) != len(records):
            raise ValueError("execution step IDs must be unique")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "events", tuple(self.events))

    def record(self, step_id: str) -> ExecutionStepRecord:
        for item in self.records:
            if item.step_id == step_id:
                return item
        raise KeyError(f"unknown execution step: {step_id}")


@dataclass(frozen=True)
class ExecutionFeedback:
    step_id: str
    prediction_evaluation: PredictionEvaluation | None = None
    observed_effects: Mapping[str, object] | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.step_id, str) or not self.step_id.strip():
            raise ValueError("step_id must be non-empty")
        if self.prediction_evaluation is not None and not isinstance(
            self.prediction_evaluation, PredictionEvaluation
        ):
            raise TypeError("prediction_evaluation must be PredictionEvaluation or None")
        object.__setattr__(
            self, "observed_effects",
            MappingProxyType(dict(self.observed_effects or {})),
        )
        object.__setattr__(self, "evidence_refs", tuple(self.evidence_refs))

    @property
    def deviation_detected(self) -> bool:
        evaluation = self.prediction_evaluation
        return bool(
            evaluation is not None
            and (evaluation.mismatched_keys or evaluation.missing_keys)
        )


@dataclass(frozen=True)
class RecoveryPolicy:
    max_retries: int = 2
    allow_replanning: bool = True
    pause_on_deviation: bool = False
    human_review_risks: frozenset[StepRisk] = frozenset(
        {StepRisk.HIGH, StepRisk.CRITICAL}
    )

    def __post_init__(self):
        if isinstance(self.max_retries, bool) or not isinstance(self.max_retries, int) or self.max_retries < 0:
            raise ValueError("max_retries must be a non-negative integer")
        if not isinstance(self.allow_replanning, bool) or not isinstance(self.pause_on_deviation, bool):
            raise TypeError("recovery policy flags must be boolean")
        risks = frozenset(self.human_review_risks)
        if any(not isinstance(item, StepRisk) for item in risks):
            raise TypeError("human_review_risks must contain StepRisk values")
        object.__setattr__(self, "human_review_risks", risks)


@dataclass(frozen=True)
class RecoveryDecision:
    action: RecoveryAction
    step_id: str
    reason: str
    attempts: int
    deviation_detected: bool = False
    requires_new_plan: bool = False

    def __post_init__(self):
        if not isinstance(self.action, RecoveryAction):
            raise TypeError("action must be RecoveryAction")
        if not isinstance(self.step_id, str) or not self.step_id.strip():
            raise ValueError("step_id must be non-empty")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must be non-empty")
        if isinstance(self.attempts, bool) or not isinstance(self.attempts, int) or self.attempts < 0:
            raise ValueError("attempts must be non-negative")


def _append_event(snapshot, event_type, step_id, timestamp=None, details=None):
    event = ExecutionEvent(
        sequence=len(snapshot.events) + 1,
        event_type=event_type,
        step_id=step_id,
        timestamp=timestamp,
        details=details,
    )
    return ExecutionSnapshot(
        plan_id=snapshot.plan_id,
        plan_version=snapshot.plan_version,
        world_revision=snapshot.world_revision,
        records=snapshot.records,
        events=snapshot.events + (event,),
    )


def _replace_record(snapshot, updated):
    records = tuple(
        updated if item.step_id == updated.step_id else item
        for item in snapshot.records
    )
    return ExecutionSnapshot(
        plan_id=snapshot.plan_id,
        plan_version=snapshot.plan_version,
        world_revision=snapshot.world_revision,
        records=records,
        events=snapshot.events,
    )


def initialize_execution(plan: Plan, world_revision: int) -> ExecutionSnapshot:
    """Create a monitoring snapshot. No action is executed."""
    if not isinstance(plan, Plan):
        raise TypeError("plan must be a Plan")
    if isinstance(world_revision, bool) or not isinstance(world_revision, int) or world_revision < 0:
        raise ValueError("world_revision must be a non-negative integer")

    return ExecutionSnapshot(
        plan_id=plan.plan_id,
        plan_version=plan.version,
        world_revision=world_revision,
        records=tuple(ExecutionStepRecord(step_id=item.step_id) for item in plan.steps),
    )


def _validate_plan_snapshot(plan, snapshot):
    if not isinstance(plan, Plan) or not isinstance(snapshot, ExecutionSnapshot):
        raise TypeError("plan and snapshot have invalid types")
    if plan.plan_id != snapshot.plan_id:
        raise ValueError("snapshot belongs to a different plan")
    if plan.version != snapshot.plan_version:
        raise ValueError("plan version is stale relative to execution snapshot")
    if {item.step_id for item in plan.steps} != {item.step_id for item in snapshot.records}:
        raise ValueError("plan steps do not match execution records")


def mark_step_started(
    plan: Plan,
    snapshot: ExecutionSnapshot,
    step_id: str,
    *,
    approval_granted: bool = False,
    timestamp: str | None = None,
) -> ExecutionSnapshot:
    """Record that an external executor has started a step."""
    _validate_plan_snapshot(plan, snapshot)
    if not isinstance(approval_granted, bool):
        raise TypeError("approval_granted must be boolean")

    step = next((item for item in plan.steps if item.step_id == step_id), None)
    if step is None:
        raise KeyError(f"unknown plan step: {step_id}")

    record = snapshot.record(step_id)
    if record.status not in (ExecutionStepStatus.PENDING, ExecutionStepStatus.FAILED):
        raise ValueError("step cannot be started from its current status")

    if step.requires_human_approval and not approval_granted:
        raise PermissionError("step requires explicit human approval")

    for dependency_id in step.depends_on:
        dependency = snapshot.record(dependency_id)
        if dependency.status is not ExecutionStepStatus.SUCCEEDED:
            raise ValueError(f"dependency {dependency_id} has not succeeded")

    updated = ExecutionStepRecord(
        step_id=step_id,
        status=ExecutionStepStatus.RUNNING,
        attempts=record.attempts + 1,
        evidence_refs=record.evidence_refs,
    )
    result = _replace_record(snapshot, updated)
    return _append_event(
        result, ExecutionEventType.STARTED, step_id, timestamp,
        {"attempt": updated.attempts},
    )


def record_step_success(
    plan: Plan,
    snapshot: ExecutionSnapshot,
    step_id: str,
    *,
    observed_effects: Mapping[str, object] | None = None,
    evidence_refs: tuple[str, ...] = (),
    timestamp: str | None = None,
) -> ExecutionSnapshot:
    _validate_plan_snapshot(plan, snapshot)
    record = snapshot.record(step_id)
    if record.status is not ExecutionStepStatus.RUNNING:
        raise ValueError("only a running step can succeed")

    updated = ExecutionStepRecord(
        step_id=step_id,
        status=ExecutionStepStatus.SUCCEEDED,
        attempts=record.attempts,
        observed_effects=observed_effects,
        evidence_refs=record.evidence_refs + tuple(evidence_refs),
    )
    result = _replace_record(snapshot, updated)
    return _append_event(result, ExecutionEventType.SUCCEEDED, step_id, timestamp)


def record_step_failure(
    plan: Plan,
    snapshot: ExecutionSnapshot,
    step_id: str,
    error: str,
    *,
    timestamp: str | None = None,
) -> ExecutionSnapshot:
    _validate_plan_snapshot(plan, snapshot)
    if not isinstance(error, str) or not error.strip():
        raise ValueError("error must be non-empty")

    record = snapshot.record(step_id)
    if record.status is not ExecutionStepStatus.RUNNING:
        raise ValueError("only a running step can fail")

    updated = ExecutionStepRecord(
        step_id=step_id,
        status=ExecutionStepStatus.FAILED,
        attempts=record.attempts,
        error=error,
        observed_effects=record.observed_effects,
        evidence_refs=record.evidence_refs,
    )
    result = _replace_record(snapshot, updated)
    return _append_event(
        result, ExecutionEventType.FAILED, step_id, timestamp,
        {"error": error},
    )


def record_execution_feedback(
    plan: Plan,
    snapshot: ExecutionSnapshot,
    feedback: ExecutionFeedback,
    *,
    timestamp: str | None = None,
) -> ExecutionSnapshot:
    """Attach observed evidence and prediction comparison to a step."""
    _validate_plan_snapshot(plan, snapshot)
    if not isinstance(feedback, ExecutionFeedback):
        raise TypeError("feedback must be ExecutionFeedback")

    record = snapshot.record(feedback.step_id)
    if record.status not in (
        ExecutionStepStatus.RUNNING,
        ExecutionStepStatus.SUCCEEDED,
        ExecutionStepStatus.FAILED,
    ):
        raise ValueError("feedback requires a started step")

    updated = ExecutionStepRecord(
        step_id=record.step_id,
        status=record.status,
        attempts=record.attempts,
        error=record.error,
        observed_effects=feedback.observed_effects,
        evidence_refs=record.evidence_refs + feedback.evidence_refs,
    )
    result = _replace_record(snapshot, updated)

    return _append_event(
        result,
        ExecutionEventType.FEEDBACK_RECEIVED,
        feedback.step_id,
        timestamp,
        {
            "deviation_detected": bool(
                feedback.prediction_evaluation
                and (
                    feedback.prediction_evaluation.mismatched_keys
                    or feedback.prediction_evaluation.missing_keys
                )
            ),
            "mismatched_keys": (
                feedback.prediction_evaluation.mismatched_keys
                if feedback.prediction_evaluation else ()
            ),
            "missing_keys": (
                feedback.prediction_evaluation.missing_keys
                if feedback.prediction_evaluation else ()
            ),
        },
    )


def evaluate_recovery(
    plan: Plan,
    snapshot: ExecutionSnapshot,
    step_id: str,
    *,
    policy: RecoveryPolicy | None = None,
    feedback: ExecutionFeedback | None = None,
    current_world_revision: int | None = None,
) -> RecoveryDecision:
    """Recommend a recovery action without executing it."""
    _validate_plan_snapshot(plan, snapshot)
    policy = policy or RecoveryPolicy()
    if not isinstance(policy, RecoveryPolicy):
        raise TypeError("policy must be RecoveryPolicy")

    step = next((item for item in plan.steps if item.step_id == step_id), None)
    if step is None:
        raise KeyError(f"unknown plan step: {step_id}")

    record = snapshot.record(step_id)
    if record.status not in (ExecutionStepStatus.FAILED, ExecutionStepStatus.SUCCEEDED):
        raise ValueError("recovery assessment requires a completed or failed attempt")

    if current_world_revision is not None:
        if isinstance(current_world_revision, bool) or not isinstance(current_world_revision, int) or current_world_revision < 0:
            raise ValueError("current_world_revision must be non-negative")
    stale_world = (
        current_world_revision is not None
        and current_world_revision != snapshot.world_revision
    )
    deviation = bool(
        feedback
        and feedback.prediction_evaluation
        and (
            feedback.prediction_evaluation.mismatched_keys
            or feedback.prediction_evaluation.missing_keys
        )
    )

    if step.risk in policy.human_review_risks or step.requires_human_approval:
        action = RecoveryAction.HUMAN_REVIEW
        reason = "step risk or approval requirements require human oversight"
    elif stale_world:
        action = RecoveryAction.REPLAN
        reason = "world revision changed; existing plan may be stale"
    elif deviation:
        if policy.pause_on_deviation:
            action = RecoveryAction.PAUSE
            reason = "observed effects deviate from prediction; policy requires pause"
        elif policy.allow_replanning:
            action = RecoveryAction.REPLAN
            reason = "observed effects deviate from prediction"
        else:
            action = RecoveryAction.HUMAN_REVIEW
            reason = "deviation detected and automatic replanning is disabled"
    elif record.status is ExecutionStepStatus.SUCCEEDED:
        action = RecoveryAction.CONTINUE
        reason = "step succeeded; dependent work may be considered"
    elif record.attempts <= policy.max_retries:
        action = RecoveryAction.RETRY
        reason = "retry budget remains"
    elif policy.allow_replanning:
        action = RecoveryAction.REPLAN
        reason = "retry budget exhausted"
    else:
        action = RecoveryAction.PAUSE
        reason = "retry budget exhausted and replanning is disabled"

    return RecoveryDecision(
        action=action,
        step_id=step_id,
        reason=reason,
        attempts=record.attempts,
        deviation_detected=deviation,
        requires_new_plan=action is RecoveryAction.REPLAN,
    )


def record_recovery_recommendation(
    snapshot: ExecutionSnapshot,
    decision: RecoveryDecision,
    *,
    timestamp: str | None = None,
) -> ExecutionSnapshot:
    """Append a recovery recommendation to the audit trace."""
    if not isinstance(snapshot, ExecutionSnapshot) or not isinstance(decision, RecoveryDecision):
        raise TypeError("invalid snapshot or recovery decision")
    snapshot.record(decision.step_id)
    return _append_event(
        snapshot,
        ExecutionEventType.RECOVERY_RECOMMENDED,
        decision.step_id,
        timestamp,
        {
            "action": decision.action.value,
            "reason": decision.reason,
            "attempts": decision.attempts,
            "deviation_detected": decision.deviation_detected,
        },
    )

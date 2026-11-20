"""Framework-neutral, immutable domain models for cognitive planning.

Models contain provenance and uncertainty; they do not execute actions or
establish clinical truth. Structured values are restricted to JSON-compatible
data and recursively frozen to make snapshots and plans safe to reuse.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any
from uuid import uuid4


def _aware_datetime(value: str, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone.")
    return parsed.astimezone(timezone.utc)


def _aware_timestamp(value: str, field_name: str) -> str:
    _aware_datetime(value, field_name)
    return value


def _non_empty(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty.")


def _finite_number(value: Any, field_name: str, *, minimum: float | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{field_name} must be a finite number.")
    if minimum is not None and value < minimum:
        raise ValueError(f"{field_name} must be >= {minimum}.")


def _freeze_json(value: Any, field_name: str = "value") -> Any:
    """Copy and recursively freeze JSON-compatible values."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        _finite_number(value, field_name)
        return value
    if isinstance(value, Mapping):
        frozen = {}
        for key, item in value.items():
            _non_empty(key, f"{field_name} key")
            frozen[key] = _freeze_json(item, f"{field_name}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, field_name) for item in value)
    raise ValueError(f"{field_name} must contain only JSON-compatible values.")


class GoalPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class StepRisk(str, Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class PlanStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    HUMAN_REVIEW = "human_review"
    COMPLETED = "completed"
    FAILED = "failed"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class StateFact:
    """A sourced assertion about the world or a patient at a point in time."""
    key: str
    value: Any
    observed_at: str
    source_type: str
    source_id: str
    confidence: float = 1.0
    valid_from: str | None = None
    valid_until: str | None = None
    sensitivity: str = "ordinary"

    def __post_init__(self) -> None:
        _non_empty(self.key, "StateFact.key")
        _non_empty(self.source_type, "StateFact.source_type")
        _non_empty(self.source_id, "StateFact.source_id")
        _non_empty(self.sensitivity, "StateFact.sensitivity")
        _finite_number(self.confidence, "StateFact.confidence", minimum=0.0)
        if self.confidence > 1.0:
            raise ValueError("StateFact.confidence must be <= 1.")
        observed = _aware_datetime(self.observed_at, "observed_at")
        valid_from = _aware_datetime(self.valid_from, "valid_from") if self.valid_from is not None else None
        valid_until = _aware_datetime(self.valid_until, "valid_until") if self.valid_until is not None else None
        if valid_from is not None and valid_until is not None and valid_from > valid_until:
            raise ValueError("valid_from must not be later than valid_until.")
        if valid_until is not None and valid_until < observed:
            # Expired facts are allowed: they remain useful historical evidence.
            pass
        object.__setattr__(self, "value", _freeze_json(self.value, "StateFact.value"))


@dataclass(frozen=True)
class StateSnapshot:
    """A versioned, provenance-aware state snapshot."""
    subject_id: str
    domain: str
    revision: int
    as_of: str
    facts: tuple[StateFact, ...] = ()
    constraints: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _non_empty(self.subject_id, "StateSnapshot.subject_id")
        _non_empty(self.domain, "StateSnapshot.domain")
        if isinstance(self.revision, bool) or not isinstance(self.revision, int) or self.revision < 0:
            raise ValueError("StateSnapshot.revision must be a non-negative integer.")
        _aware_timestamp(self.as_of, "as_of")
        keys = [fact.key for fact in self.facts]
        if len(keys) != len(set(keys)):
            raise ValueError("StateSnapshot fact keys must be unique.")
        for item in self.constraints + self.unknowns:
            _non_empty(item, "StateSnapshot constraint/unknown")


@dataclass(frozen=True)
class BeliefHypothesis:
    """An uncertain hypothesis; probability is not a diagnosis or truth claim."""
    hypothesis_id: str
    statement: str
    probability: float
    evidence_refs: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _non_empty(self.hypothesis_id, "BeliefHypothesis.hypothesis_id")
        _non_empty(self.statement, "BeliefHypothesis.statement")
        _finite_number(self.probability, "BeliefHypothesis.probability", minimum=0.0)
        if self.probability > 1.0:
            raise ValueError("BeliefHypothesis.probability must be <= 1.")
        for ref in self.evidence_refs:
            _non_empty(ref, "BeliefHypothesis.evidence_ref")


@dataclass(frozen=True)
class BeliefState:
    snapshot: StateSnapshot
    hypotheses: tuple[BeliefHypothesis, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    confidence_threshold: float = 0.8

    def __post_init__(self) -> None:
        _finite_number(self.confidence_threshold, "confidence_threshold", minimum=0.0)
        if self.confidence_threshold > 1.0:
            raise ValueError("confidence_threshold must be <= 1.")
        ids = [item.hypothesis_id for item in self.hypotheses]
        if len(ids) != len(set(ids)):
            raise ValueError("BeliefState hypothesis ids must be unique.")
        for item in self.unresolved_questions:
            _non_empty(item, "unresolved_question")

    def fact(self, key: str) -> StateFact | None:
        return next((item for item in self.snapshot.facts if item.key == key), None)

    def is_known(self, key: str) -> bool:
        item = self.fact(key)
        return item is not None and item.confidence >= self.confidence_threshold


@dataclass(frozen=True)
class Goal:
    goal_id: str
    description: str
    domain: str
    priority: GoalPriority = GoalPriority.NORMAL
    success_criteria: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    deadline: str | None = None
    parent_goal_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _non_empty(self.goal_id, "Goal.goal_id")
        _non_empty(self.description, "Goal.description")
        _non_empty(self.domain, "Goal.domain")
        if self.deadline is not None:
            _aware_timestamp(self.deadline, "Goal.deadline")
        object.__setattr__(self, "metadata", _freeze_json(self.metadata, "Goal.metadata"))


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    action: str
    description: str
    depends_on: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    effects: Mapping[str, Any] = field(default_factory=dict)
    risk: StepRisk = StepRisk.LOW
    requires_human_approval: bool = False
    expected_duration_seconds: int | None = None
    resource_requirements: Mapping[str, float] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _non_empty(self.step_id, "PlanStep.step_id")
        _non_empty(self.action, "PlanStep.action")
        _non_empty(self.description, "PlanStep.description")
        if self.expected_duration_seconds is not None:
            if isinstance(self.expected_duration_seconds, bool) or not isinstance(self.expected_duration_seconds, int) or self.expected_duration_seconds < 0:
                raise ValueError("expected_duration_seconds must be a non-negative integer.")
        for dep in self.depends_on:
            _non_empty(dep, "PlanStep dependency")
        for ref in self.evidence_refs:
            _non_empty(ref, "PlanStep evidence_ref")
        for key, value in self.resource_requirements.items():
            _non_empty(key, "resource name")
            _finite_number(value, f"resource_requirements[{key!r}]", minimum=0.0)
        object.__setattr__(self, "effects", _freeze_json(self.effects, "PlanStep.effects"))
        object.__setattr__(self, "resource_requirements", _freeze_json(self.resource_requirements, "PlanStep.resource_requirements"))
        object.__setattr__(self, "metadata", _freeze_json(self.metadata, "PlanStep.metadata"))


@dataclass(frozen=True)
class Plan:
    plan_id: str
    goal_id: str
    domain: str
    state_revision: int
    steps: tuple[PlanStep, ...]
    created_at: str
    version: int = 1
    status: PlanStatus = PlanStatus.DRAFT
    rationale: str = ""
    assumptions: tuple[str, ...] = ()
    unresolved_risks: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        goal: Goal,
        state: StateSnapshot,
        steps: tuple[PlanStep, ...],
        *,
        rationale: str = "",
        assumptions: tuple[str, ...] = (),
    ) -> "Plan":
        if goal.domain.casefold() != state.domain.casefold():
            raise ValueError("Goal.domain must match StateSnapshot.domain.")
        return cls(
            plan_id=str(uuid4()),
            goal_id=goal.goal_id,
            domain=goal.domain,
            state_revision=state.revision,
            steps=steps,
            created_at=datetime.now(timezone.utc).isoformat(),
            rationale=rationale,
            assumptions=assumptions,
        )

    def __post_init__(self) -> None:
        _non_empty(self.plan_id, "Plan.plan_id")
        _non_empty(self.goal_id, "Plan.goal_id")
        _non_empty(self.domain, "Plan.domain")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("Plan.version must be a positive integer.")
        if isinstance(self.state_revision, bool) or not isinstance(self.state_revision, int) or self.state_revision < 0:
            raise ValueError("Plan.state_revision must be a non-negative integer.")
        _aware_timestamp(self.created_at, "Plan.created_at")
        object.__setattr__(self, "metadata", _freeze_json(self.metadata, "Plan.metadata"))
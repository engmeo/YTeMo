"""Domain-neutral contracts for composing cognitive planning stages.

This module defines pipeline data contracts only. It does not execute actions,
dispatch tools, persist state, or depend on any application domain.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from .models import Goal, Plan, StateSnapshot


class PipelineStage(str, Enum):
    INTAKE = "intake"
    WORLD_MODEL = "world_model"
    HTN_PLANNING = "htn_planning"
    STRATEGY_PLANNING = "strategy_planning"
    DECISION = "decision"
    MULTI_AGENT_ALLOCATION = "multi_agent_allocation"
    VALIDATION = "validation"
    SCHEDULING = "scheduling"
    GOVERNANCE = "governance"
    EXECUTION_MONITORING = "execution_monitoring"
    RECOVERY = "recovery"
    REPLANNING = "replanning"
    META_COGNITION = "meta_cognition"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"
    HUMAN_REVIEW = "human_review"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    FAILED = "failed"
    HUMAN_REVIEW = "human_review"
    CANCELLED = "cancelled"


def _require_aware_datetime(value: datetime | None, name: str) -> None:
    if value is None:
        return
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime or None")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def _freeze_metadata(value: Any, path: str = "metadata") -> Any:
    """Recursively freeze JSON-compatible metadata."""
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return value

    if isinstance(value, Mapping):
        frozen = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} keys must be strings")
            frozen[key] = _freeze_metadata(item, f"{path}.{key}")
        return MappingProxyType(frozen)

    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_metadata(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        )

    raise TypeError(
        f"{path} must contain only JSON-compatible values; "
        f"got {type(value).__name__}"
    )


def _validate_unique_enum_values(values: tuple, enum_type: type, name: str) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{name} must be a tuple")
    if any(not isinstance(value, enum_type) for value in values):
        raise TypeError(f"{name} contains an invalid value")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} must not contain duplicates")


@dataclass(frozen=True)
class PipelinePolicy:
    """Cross-stage policy; stage-specific policies remain with their engines."""

    required_stages: tuple[PipelineStage, ...] = ()
    governance_required: bool = False
    stop_on_stage_failure: bool = True
    allow_partial_results: bool = True
    require_provenance: bool = True
    version: str = "1"

    def __post_init__(self) -> None:
        _validate_unique_enum_values(
            self.required_stages, PipelineStage, "required_stages"
        )
        if not isinstance(self.governance_required, bool):
            raise TypeError("governance_required must be bool")
        if not isinstance(self.stop_on_stage_failure, bool):
            raise TypeError("stop_on_stage_failure must be bool")
        if not isinstance(self.allow_partial_results, bool):
            raise TypeError("allow_partial_results must be bool")
        if not isinstance(self.require_provenance, bool):
            raise TypeError("require_provenance must be bool")
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("version must be a non-empty string")


@dataclass(frozen=True)
class PipelineRequest:
    """An explicit request to compose a selected set of planning stages."""

    goal: Goal
    state: StateSnapshot
    enabled_stages: tuple[PipelineStage, ...]
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    policy: PipelinePolicy = field(default_factory=PipelinePolicy)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.goal, Goal):
            raise TypeError("goal must be a Goal")
        if not isinstance(self.state, StateSnapshot):
            raise TypeError("state must be a StateSnapshot")
        if self.goal.domain != self.state.domain:
            raise ValueError("goal and state domains must match")

        _validate_unique_enum_values(
            self.enabled_stages, PipelineStage, "enabled_stages"
        )
        if not self.enabled_stages:
            raise ValueError("enabled_stages must not be empty")

        if not isinstance(self.policy, PipelinePolicy):
            raise TypeError("policy must be a PipelinePolicy")

        enabled = set(self.enabled_stages)
        missing = set(self.policy.required_stages) - enabled
        if missing:
            names = sorted(stage.value for stage in missing)
            raise ValueError(f"required stages are not enabled: {names}")

        if self.policy.governance_required and PipelineStage.GOVERNANCE not in enabled:
            raise ValueError("governance is required but not enabled")

        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError("request_id must be a non-empty string")

        object.__setattr__(
            self, "metadata", _freeze_metadata(self.metadata)
        )


@dataclass(frozen=True)
class StageProvenance:
    """Origin and revision information for one stage result."""

    stage: PipelineStage
    component: str
    component_version: str
    input_revision: int | None = None
    output_revision: int | None = None
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.stage, PipelineStage):
            raise TypeError("stage must be a PipelineStage")
        for name in ("component", "component_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

        for name in ("input_revision", "output_revision"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 0
            ):
                raise ValueError(f"{name} must be a non-negative integer or None")

        if not isinstance(self.evidence_refs, tuple):
            raise TypeError("evidence_refs must be a tuple")
        if any(not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs):
            raise ValueError("evidence_refs must contain non-empty strings")

        object.__setattr__(
            self, "metadata", _freeze_metadata(self.metadata)
        )


@dataclass(frozen=True)
class PipelineStageResult:
    """A stage outcome retaining its original engine output."""

    stage: PipelineStage
    status: StageStatus
    output: object | None = None
    provenance: StageProvenance | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    issues: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.stage, PipelineStage):
            raise TypeError("stage must be a PipelineStage")
        if not isinstance(self.status, StageStatus):
            raise TypeError("status must be a StageStatus")
        if self.provenance is not None:
            if not isinstance(self.provenance, StageProvenance):
                raise TypeError("provenance must be StageProvenance or None")
            if self.provenance.stage != self.stage:
                raise ValueError("provenance stage must match result stage")

        _require_aware_datetime(self.started_at, "started_at")
        _require_aware_datetime(self.completed_at, "completed_at")
        if self.completed_at is not None and self.started_at is None:
            raise ValueError("completed_at requires started_at")
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError("completed_at cannot precede started_at")

        if not isinstance(self.issues, tuple):
            raise TypeError("issues must be a tuple")
        if any(not isinstance(issue, str) for issue in self.issues):
            raise TypeError("issues must contain strings")
        if self.reason is not None and not isinstance(self.reason, str):
            raise TypeError("reason must be a string or None")


@dataclass(frozen=True)
class PipelineResult:
    """Immutable aggregate result; it does not authorize action execution."""

    request_id: str
    goal_id: str
    domain: str
    status: PipelineStatus
    stage_results: tuple[PipelineStageResult, ...]
    started_at: datetime
    completed_at: datetime | None = None
    plan: Plan | None = None
    reasons: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("request_id", "goal_id", "domain"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

        if not isinstance(self.status, PipelineStatus):
            raise TypeError("status must be a PipelineStatus")
        if not isinstance(self.stage_results, tuple):
            raise TypeError("stage_results must be a tuple")
        if any(not isinstance(item, PipelineStageResult) for item in self.stage_results):
            raise TypeError("stage_results must contain PipelineStageResult values")

        stages = tuple(item.stage for item in self.stage_results)
        if len(stages) != len(set(stages)):
            raise ValueError("stage_results must not contain duplicate stages")

        _require_aware_datetime(self.started_at, "started_at")
        _require_aware_datetime(self.completed_at, "completed_at")
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot precede started_at")

        if self.plan is not None:
            if not isinstance(self.plan, Plan):
                raise TypeError("plan must be a Plan or None")
            if self.plan.goal_id != self.goal_id or self.plan.domain != self.domain:
                raise ValueError("plan identity must match pipeline result")

        if not isinstance(self.reasons, tuple):
            raise TypeError("reasons must be a tuple")
        if any(not isinstance(reason, str) for reason in self.reasons):
            raise TypeError("reasons must contain strings")

        object.__setattr__(
            self, "metadata", _freeze_metadata(self.metadata)
        )
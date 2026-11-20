"""Deterministic, non-executing plan scheduling and transparent evaluation.

The scheduler produces a resource-feasible timeline. It never invokes tools,
agents, external services, or clinical actions.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from types import MappingProxyType
from typing import Mapping

from .contracts import DomainPolicy
from .models import Plan, StepRisk
from .validation import validate_plan


@dataclass(frozen=True)
class ScheduleIssue:
    code: str
    message: str
    step_id: str | None = None


@dataclass(frozen=True)
class ScheduledStep:
    step_id: str
    start_seconds: int
    finish_seconds: int
    resource_requirements: Mapping[str, float]
    requires_human_approval: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "resource_requirements",
            MappingProxyType(dict(self.resource_requirements)),
        )


@dataclass(frozen=True)
class ScheduleResult:
    feasible: bool
    steps: tuple[ScheduledStep, ...]
    issues: tuple[ScheduleIssue, ...]
    makespan_seconds: int | None

    @property
    def by_step_id(self) -> Mapping[str, ScheduledStep]:
        return MappingProxyType({item.step_id: item for item in self.steps})


@dataclass(frozen=True)
class PlanMetrics:
    step_count: int
    total_work_seconds: int | None
    critical_path_seconds: int | None
    high_risk_step_count: int
    critical_risk_step_count: int
    human_approval_step_count: int
    duration_complete: bool


def _finite_nonnegative(value: object, label: str) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and isfinite(value)
        and value >= 0
    )


def schedule_plan(
    plan: Plan,
    resource_capacities: Mapping[str, float] | None = None,
    *,
    max_parallel_steps: int = 4,
    domain_policy: DomainPolicy | None = None,
) -> ScheduleResult:
    """Create a deterministic earliest-start schedule from a validated DAG.

    Resource capacities are simultaneous capacities, not cumulative budgets.
    Steps are considered in lexicographic step_id order when several are ready.
    """
    if isinstance(max_parallel_steps, bool) or not isinstance(max_parallel_steps, int) or max_parallel_steps < 1:
        raise ValueError("max_parallel_steps must be a positive integer.")

    capacities = dict(resource_capacities or {})
    issues: list[ScheduleIssue] = []
    for name, capacity in capacities.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Resource capacity names must be non-empty strings.")
        if not _finite_nonnegative(capacity, f"capacity[{name}]"):
            raise ValueError(f"Resource capacity for {name!r} must be finite and non-negative.")

    validation = validate_plan(plan, domain_policy=domain_policy)
    if not validation.valid:
        return ScheduleResult(
            feasible=False,
            steps=(),
            issues=tuple(
                ScheduleIssue(item.code, item.message, item.step_id)
                for item in validation.blocking_issues
            ),
            makespan_seconds=None,
        )

    by_id = {step.step_id: step for step in plan.steps}
    for step in plan.steps:
        if step.expected_duration_seconds is None:
            issues.append(ScheduleIssue(
                "missing_duration",
                "A duration is required to construct a schedule.",
                step.step_id,
            ))
        for resource, required in step.resource_requirements.items():
            if resource not in capacities:
                issues.append(ScheduleIssue(
                    "unknown_resource",
                    f"No capacity was supplied for resource {resource!r}.",
                    step.step_id,
                ))
            elif required > capacities[resource]:
                issues.append(ScheduleIssue(
                    "resource_demand_exceeds_capacity",
                    f"Step requires {required} of {resource}, capacity is {capacities[resource]}.",
                    step.step_id,
                ))

    if issues:
        return ScheduleResult(False, (), tuple(issues), None)

    remaining = set(by_id)
    completed: set[str] = set()
    running: list[ScheduledStep] = []
    scheduled: list[ScheduledStep] = []
    current_time = 0

    while remaining or running:
        newly_completed = [
            item for item in running if item.finish_seconds <= current_time
        ]
        for item in newly_completed:
            completed.add(item.step_id)
        if newly_completed:
            running = [
                item for item in running if item.finish_seconds > current_time
            ]

        # All steps have completed; this is success, not a scheduler deadlock.
        if not remaining and not running:
            break

        active_usage = {name: 0.0 for name in capacities}
        for item in running:
            for name, amount in item.resource_requirements.items():
                active_usage[name] += amount

        ready = sorted(
            step_id for step_id in remaining
            if set(by_id[step_id].depends_on).issubset(completed)
        )
        started_any = False

        for step_id in ready:
            if len(running) >= max_parallel_steps:
                break
            step = by_id[step_id]
            requirements = step.resource_requirements
            fits = all(
                active_usage[name] + amount <= capacities[name]
                for name, amount in requirements.items()
            )
            if not fits:
                continue

            duration = step.expected_duration_seconds
            # Missing durations were rejected in preflight.
            assert duration is not None
            item = ScheduledStep(
                step_id=step_id,
                start_seconds=current_time,
                finish_seconds=current_time + duration,
                resource_requirements=requirements,
                requires_human_approval=step.requires_human_approval,
            )
            scheduled.append(item)
            running.append(item)
            for name, amount in requirements.items():
                active_usage[name] += amount
            remaining.remove(step_id)
            started_any = True

        if started_any:
            continue

        if running:
            next_finish = min(item.finish_seconds for item in running)
            if next_finish <= current_time:
                # Zero-duration steps are completed on the next loop pass.
                continue
            current_time = next_finish
            continue

        # A validated DAG with feasible resource declarations should not deadlock.
        return ScheduleResult(
            False, tuple(scheduled),
            (ScheduleIssue("scheduler_deadlock", "No remaining step can be scheduled."),),
            None,
        )

    ordered = tuple(sorted(scheduled, key=lambda item: (item.start_seconds, item.step_id)))
    makespan = max((item.finish_seconds for item in ordered), default=0)
    return ScheduleResult(True, ordered, (), makespan)


def evaluate_plan(plan: Plan, domain_policy: DomainPolicy | None = None) -> PlanMetrics:
    """Return explainable structural metrics; deliberately avoids arbitrary scores."""
    validation = validate_plan(plan, domain_policy=domain_policy)
    if not validation.valid:
        raise ValueError("Cannot evaluate an invalid plan.")

    durations = {
        step.step_id: step.expected_duration_seconds
        for step in plan.steps
    }
    duration_complete = all(value is not None for value in durations.values())
    total_work = (
        sum(value for value in durations.values() if value is not None)
        if duration_complete else None
    )

    critical_path: int | None = None
    if duration_complete:
        longest_finish: dict[str, int] = {}
        for step_id in validation.topological_order:
            step = next(item for item in plan.steps if item.step_id == step_id)
            predecessor_finish = max(
                (longest_finish[dep] for dep in step.depends_on),
                default=0,
            )
            longest_finish[step_id] = predecessor_finish + (step.expected_duration_seconds or 0)
        critical_path = max(longest_finish.values(), default=0)

    return PlanMetrics(
        step_count=len(plan.steps),
        total_work_seconds=total_work,
        critical_path_seconds=critical_path,
        high_risk_step_count=sum(step.risk == StepRisk.HIGH for step in plan.steps),
        critical_risk_step_count=sum(step.risk == StepRisk.CRITICAL for step in plan.steps),
        human_approval_step_count=sum(step.requires_human_approval for step in plan.steps),
        duration_complete=duration_complete,
    )
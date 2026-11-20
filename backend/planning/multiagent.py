"""Domain-neutral multi-agent planning and task allocation.

This module produces auditable task assignment recommendations.
It does not invoke agents, execute tasks, or grant execution permissions.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Optional, Sequence


class AllocationStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    HUMAN_REVIEW = "human_review"
    NO_FEASIBLE_ASSIGNMENT = "no_feasible_assignment"


class ConflictKind(str, Enum):
    NO_ELIGIBLE_BID = "no_eligible_bid"
    DEPENDENCY_UNASSIGNED = "dependency_unassigned"
    UNKNOWN_AGENT = "unknown_agent"
    UNKNOWN_TASK = "unknown_task"


@dataclass(frozen=True)
class AgentDescriptor:
    agent_id: str
    capabilities: tuple[str, ...]
    max_assigned_tasks: int = 1
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise ValueError("agent_id must not be empty")
        if self.max_assigned_tasks < 1:
            raise ValueError("max_assigned_tasks must be at least 1")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("agent capabilities must be unique")
        if any(not item.strip() for item in self.capabilities):
            raise ValueError("capabilities must not contain empty values")


@dataclass(frozen=True)
class CoordinationTask:
    task_id: str
    required_capabilities: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    priority: float = 1.0
    requires_human_approval: bool = False

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must not be empty")
        if not isfinite(self.priority) or self.priority < 0:
            raise ValueError("priority must be finite and non-negative")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("task dependencies must be unique")
        if self.task_id in self.dependencies:
            raise ValueError("task cannot depend on itself")


@dataclass(frozen=True)
class AgentBid:
    agent_id: str
    task_id: str
    estimated_cost: float
    estimated_duration: float
    confidence: float
    resource_usage: tuple[tuple[str, float], ...] = ()
    safety_eligible: bool = True
    requires_human_approval: bool = False

    def __post_init__(self) -> None:
        if not self.agent_id.strip() or not self.task_id.strip():
            raise ValueError("bid agent_id and task_id must not be empty")
        for name in ("estimated_cost", "estimated_duration"):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if not isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        resource_names = [name for name, _ in self.resource_usage]
        if len(set(resource_names)) != len(resource_names):
            raise ValueError("resource names in a bid must be unique")
        for name, amount in self.resource_usage:
            if not name.strip() or not isfinite(amount) or amount < 0:
                raise ValueError("resource usage must have valid names and non-negative values")


@dataclass(frozen=True)
class MultiAgentPolicy:
    policy_version: str = "1"
    cost_weight: float = 1.0
    duration_weight: float = 0.1
    load_balance_weight: float = 0.5
    confidence_weight: float = 1.0
    priority_weight: float = 0.1
    resource_capacities: tuple[tuple[str, float], ...] = ()
    allow_partial_allocation: bool = True

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version must not be empty")
        for name in (
            "cost_weight",
            "duration_weight",
            "load_balance_weight",
            "confidence_weight",
            "priority_weight",
        ):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        names = [name for name, _ in self.resource_capacities]
        if len(set(names)) != len(names):
            raise ValueError("resource capacity names must be unique")
        for name, capacity in self.resource_capacities:
            if not name.strip() or not isfinite(capacity) or capacity < 0:
                raise ValueError("resource capacities must be valid and non-negative")


@dataclass(frozen=True)
class BidAssessment:
    agent_id: str
    task_id: str
    eligible: bool
    score: Optional[float]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class TaskAssignment:
    task_id: str
    agent_id: str
    score: float
    estimated_cost: float
    estimated_duration: float
    resource_usage: tuple[tuple[str, float], ...]
    requires_human_approval: bool


@dataclass(frozen=True)
class AllocationConflict:
    task_id: str
    kind: ConflictKind
    reason: str
    related_task_id: Optional[str] = None


@dataclass(frozen=True)
class CoordinationTrace:
    policy_version: str
    allocation_order: tuple[str, ...]
    bid_assessments: tuple[BidAssessment, ...]
    conflicts: tuple[AllocationConflict, ...]
    assignments: tuple[TaskAssignment, ...]


@dataclass(frozen=True)
class MultiAgentAllocation:
    status: AllocationStatus
    assignments: tuple[TaskAssignment, ...]
    unassigned_task_ids: tuple[str, ...]
    conflicts: tuple[AllocationConflict, ...]
    trace: CoordinationTrace


def _topological_order(
    tasks: Sequence[CoordinationTask],
) -> tuple[str, ...]:
    by_id = {task.task_id: task for task in tasks}

    if len(by_id) != len(tasks):
        raise ValueError("task_id values must be unique")

    for task in tasks:
        for dependency in task.dependencies:
            if dependency not in by_id:
                raise ValueError(
                    f"unknown dependency {dependency!r} for task {task.task_id!r}"
                )

    remaining = set(by_id)
    completed: set[str] = set()
    ordered: list[str] = []

    while remaining:
        ready = sorted(
            task_id
            for task_id in remaining
            if set(by_id[task_id].dependencies).issubset(completed)
        )
        if not ready:
            raise ValueError("task dependency graph contains a cycle")
        for task_id in ready:
            ordered.append(task_id)
            completed.add(task_id)
            remaining.remove(task_id)

    return tuple(ordered)


def allocate_tasks(
    agents: Sequence[AgentDescriptor],
    tasks: Sequence[CoordinationTask],
    bids: Sequence[AgentBid],
    policy: MultiAgentPolicy = MultiAgentPolicy(),
) -> MultiAgentAllocation:
    """Allocate tasks using capability, safety, load and resource constraints.

    All bids are treated as one bounded allocation round. The result is a
    recommendation, not an execution command or distributed consensus result.
    """

    agent_by_id = {agent.agent_id: agent for agent in agents}
    task_by_id = {task.task_id: task for task in tasks}

    if len(agent_by_id) != len(agents):
        raise ValueError("agent_id values must be unique")
    if len(task_by_id) != len(tasks):
        raise ValueError("task_id values must be unique")

    order = _topological_order(tasks)

    seen_bids: set[tuple[str, str]] = set()
    for bid in bids:
        key = (bid.agent_id, bid.task_id)
        if key in seen_bids:
            raise ValueError("duplicate bid for the same agent and task")
        seen_bids.add(key)
        if bid.task_id not in task_by_id:
            raise ValueError(f"bid references unknown task: {bid.task_id}")
        if bid.agent_id not in agent_by_id:
            raise ValueError(f"bid references unknown agent: {bid.agent_id}")

    capacities = dict(policy.resource_capacities)
    resource_used: dict[str, float] = {}
    assigned_count: dict[str, int] = {agent_id: 0 for agent_id in agent_by_id}
    assigned_tasks: dict[str, TaskAssignment] = {}
    assessments: list[BidAssessment] = []
    conflicts: list[AllocationConflict] = []

    bids_by_task: dict[str, list[AgentBid]] = {}
    for bid in bids:
        bids_by_task.setdefault(bid.task_id, []).append(bid)

    for task_id in order:
        task = task_by_id[task_id]

        missing_dependencies = [
            dependency
            for dependency in task.dependencies
            if dependency not in assigned_tasks
        ]
        if missing_dependencies:
            for dependency in missing_dependencies:
                conflicts.append(
                    AllocationConflict(
                        task_id=task_id,
                        kind=ConflictKind.DEPENDENCY_UNASSIGNED,
                        reason="required_dependency_was_not_assigned",
                        related_task_id=dependency,
                    )
                )
            continue

        eligible: list[tuple[float, AgentBid, bool]] = []

        for bid in bids_by_task.get(task_id, []):
            agent = agent_by_id[bid.agent_id]
            reasons: list[str] = []

            if not agent.enabled:
                reasons.append("agent_disabled")

            missing_capabilities = (
                set(task.required_capabilities) - set(agent.capabilities)
            )
            if missing_capabilities:
                reasons.append("missing_required_capabilities:" + ",".join(sorted(missing_capabilities)))

            if not bid.safety_eligible:
                reasons.append("excluded_by_external_safety_gate")

            if assigned_count[agent.agent_id] >= agent.max_assigned_tasks:
                reasons.append("agent_assignment_capacity_exceeded")

            for resource, amount in bid.resource_usage:
                capacity = capacities.get(resource)
                if capacity is not None:
                    used = resource_used.get(resource, 0.0)
                    if used + amount > capacity:
                        reasons.append(f"resource_capacity_exceeded:{resource}")

            is_eligible = not reasons
            score: Optional[float] = None

            if is_eligible:
                score = (
                    policy.cost_weight * bid.estimated_cost
                    + policy.duration_weight * bid.estimated_duration
                    + policy.load_balance_weight * assigned_count[agent.agent_id]
                    - policy.confidence_weight * bid.confidence
                    - policy.priority_weight * task.priority
                )
                eligible.append((score, bid, (
                    task.requires_human_approval or bid.requires_human_approval
                )))
                reasons.append("passed_capability_safety_and_capacity_checks")

            assessments.append(
                BidAssessment(
                    agent_id=bid.agent_id,
                    task_id=task_id,
                    eligible=is_eligible,
                    score=score,
                    reasons=tuple(reasons),
                )
            )

        if not eligible:
            conflicts.append(
                AllocationConflict(
                    task_id=task_id,
                    kind=ConflictKind.NO_ELIGIBLE_BID,
                    reason="no_bid_passed_all_allocation_constraints",
                )
            )
            continue

        eligible.sort(key=lambda item: (item[0], item[1].agent_id))
        score, winning_bid, needs_approval = eligible[0]

        assignment = TaskAssignment(
            task_id=task_id,
            agent_id=winning_bid.agent_id,
            score=score,
            estimated_cost=winning_bid.estimated_cost,
            estimated_duration=winning_bid.estimated_duration,
            resource_usage=winning_bid.resource_usage,
            requires_human_approval=needs_approval,
        )

        assigned_tasks[task_id] = assignment
        assigned_count[winning_bid.agent_id] += 1

        for resource, amount in winning_bid.resource_usage:
            resource_used[resource] = resource_used.get(resource, 0.0) + amount

    unassigned = tuple(task_id for task_id in order if task_id not in assigned_tasks)
    tentative_assignments = tuple(
        assigned_tasks[task_id]
        for task_id in order
        if task_id in assigned_tasks
    )

    if unassigned and not policy.allow_partial_allocation:
        final_assignments: tuple[TaskAssignment, ...] = ()
        status = AllocationStatus.NO_FEASIBLE_ASSIGNMENT
    else:
        final_assignments = tentative_assignments
        if unassigned:
            status = AllocationStatus.PARTIAL
        elif any(item.requires_human_approval for item in final_assignments):
            status = AllocationStatus.HUMAN_REVIEW
        else:
            status = AllocationStatus.COMPLETE

    trace = CoordinationTrace(
        policy_version=policy.policy_version,
        allocation_order=order,
        bid_assessments=tuple(assessments),
        conflicts=tuple(conflicts),
        assignments=final_assignments,
    )

    return MultiAgentAllocation(
        status=status,
        assignments=final_assignments,
        unassigned_task_ids=unassigned,
        conflicts=tuple(conflicts),
        trace=trace,
    )

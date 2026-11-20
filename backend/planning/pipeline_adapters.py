"""Thin adapters connecting Planning pipeline stages to existing engines.

Adapters preserve engine outputs and traces. They do not execute agents,
tools, or plans.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .decision_engine import (
    DecisionCandidate,
    DecisionPolicy,
    DecisionResult,
    select_decision,
)
from .hierarchical_adapter import hierarchical_result_to_plan
from .hierarchical_engine import (
    HierarchicalMethod,
    HierarchicalPlanResult,
    HierarchicalPlanner,
)
from .hierarchy import DecompositionMethod, Task
from .models import BeliefState, Goal, Plan, StateSnapshot
from .validation import PlanningPolicy, PlanValidationResult
from .multiagent import (
    AgentBid,
    AgentDescriptor,
    CoordinationTask,
    MultiAgentAllocation,
    MultiAgentPolicy,
    allocate_tasks,
)
from .world_model import WorldPrediction


@dataclass(frozen=True)
class HTNAdapterResult:
    """Preserve both HTN decomposition and its validated Plan conversion."""

    decomposition: HierarchicalPlanResult
    plan: Plan
    validation: PlanValidationResult


def run_htn_adapter(
    *,
    goal: Goal,
    state: StateSnapshot,
    tasks: Sequence[Task],
    methods: Sequence[DecompositionMethod | HierarchicalMethod],
    context: Mapping[str, object] | None = None,
    dependencies: Mapping[str, Sequence[str]] | None = None,
    planner: HierarchicalPlanner | None = None,
    task_payload_defaults: Mapping[str, Mapping[str, object]] | None = None,
    policy: PlanningPolicy | None = None,
) -> HTNAdapterResult:
    """Run HTN decomposition and convert its result without executing it."""
    active_planner = planner if planner is not None else HierarchicalPlanner()
    decomposition = active_planner.plan(
        tasks,
        methods,
        context=context,
        dependencies=dependencies,
    )
    plan, validation = hierarchical_result_to_plan(
        goal,
        state,
        decomposition,
        task_payload_defaults=task_payload_defaults,
        policy=policy,
    )
    return HTNAdapterResult(
        decomposition=decomposition,
        plan=plan,
        validation=validation,
    )


def run_decision_adapter(
    *,
    belief: BeliefState,
    candidates: tuple[DecisionCandidate, ...],
    policy: DecisionPolicy | None = None,
    world_predictions: tuple[WorldPrediction, ...] = (),
    world_revision: int | None = None,
    tie_tolerance: float = 1e-9,
) -> DecisionResult:
    """Delegate decision evaluation to the existing decision engine."""
    return select_decision(
        belief,
        candidates,
        policy,
        world_predictions=world_predictions,
        world_revision=world_revision,
        tie_tolerance=tie_tolerance,
    )


def run_multiagent_allocation_adapter(
    *,
    agents: Sequence[AgentDescriptor],
    tasks: Sequence[CoordinationTask],
    bids: Sequence[AgentBid],
    policy: MultiAgentPolicy | None = None,
) -> MultiAgentAllocation:
    """Delegate allocation to the existing multi-agent engine."""
    if policy is None:
        return allocate_tasks(agents, tasks, bids)
    return allocate_tasks(agents, tasks, bids, policy)


from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from .contracts import DomainPolicy
from .decision_engine import BeliefState, DecisionCandidate, DecisionResult
from .governance import GovernanceDecision, GovernanceRequest
from .hierarchical_engine import HierarchicalMethod
from .hierarchy import Task
from .multiagent import (
    AgentBid,
    AgentDescriptor,
    CoordinationTask,
    MultiAgentAllocation,
)
from .models import Plan
from .pipeline_contracts import PipelineRequest, PipelineStageResult
from .scheduler import PlanMetrics, ScheduleResult
from .validation import PlanValidationResult


class PipelinePlanningMode(str, Enum):
    HTN = "htn"
    STRATEGY = "strategy"


@dataclass(frozen=True)
class PipelineInputs:
    """Explicit runtime inputs required by optional planning stages."""

    planning_mode: PipelinePlanningMode

    htn_tasks: tuple[Task, ...] = ()
    htn_methods: tuple[HierarchicalMethod, ...] = ()
    htn_context: Mapping[str, object] = field(default_factory=dict)
    htn_dependencies: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    belief_state: BeliefState | None = None
    decision_candidates: tuple[DecisionCandidate, ...] = ()

    agents: tuple[AgentDescriptor, ...] = ()
    coordination_tasks: tuple[CoordinationTask, ...] = ()
    agent_bids: tuple[AgentBid, ...] = ()

    governance_request: GovernanceRequest | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.planning_mode, PipelinePlanningMode):
            raise TypeError("planning_mode must be a PipelinePlanningMode.")

        if self.planning_mode is PipelinePlanningMode.HTN:
            if not self.htn_tasks or not self.htn_methods:
                raise ValueError("HTN mode requires htn_tasks and htn_methods.")
        elif self.htn_tasks or self.htn_methods:
            raise ValueError("HTN inputs must be empty in STRATEGY mode.")

        if (self.belief_state is None) != (not self.decision_candidates):
            raise ValueError(
                "Decision requires both belief_state and decision_candidates."
            )

        multiagent_values = (
            bool(self.agents),
            bool(self.coordination_tasks),
            bool(self.agent_bids),
        )
        if any(multiagent_values) and not all(multiagent_values):
            raise ValueError(
                "Multi-Agent input requires agents, coordination_tasks and agent_bids."
            )

        if self.governance_request is not None and not isinstance(
            self.governance_request, GovernanceRequest
        ):
            raise TypeError("governance_request must be GovernanceRequest.")

        object.__setattr__(
            self, "htn_context", MappingProxyType(dict(self.htn_context))
        )
        object.__setattr__(
            self,
            "htn_dependencies",
            MappingProxyType({
                key: tuple(value)
                for key, value in self.htn_dependencies.items()
            }),
        )


@dataclass(frozen=True)
class PipelineContext:
    """Immutable state passed between Planning Pipeline stages."""

    request: PipelineRequest
    inputs: PipelineInputs

    domain_policy: DomainPolicy | None = None

    plan: Plan | None = None
    validation: PlanValidationResult | None = None
    schedule: ScheduleResult | None = None
    metrics: PlanMetrics | None = None

    decision: DecisionResult | None = None
    allocation: MultiAgentAllocation | None = None
    governance: GovernanceDecision | None = None

    stage_results: tuple[PipelineStageResult, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.request, PipelineRequest):
            raise TypeError("request must be PipelineRequest.")

        if not isinstance(self.inputs, PipelineInputs):
            raise TypeError("inputs must be PipelineInputs.")

        if self.domain_policy is not None:
            if not isinstance(self.domain_policy, DomainPolicy):
                raise TypeError("domain_policy must be DomainPolicy.")
            if self.domain_policy.domain_id.casefold() != (
                self.request.goal.domain.casefold()
            ):
                raise ValueError(
                    "DomainPolicy.domain_id must match the request domain."
                )

        if self.plan is not None:
            if not isinstance(self.plan, Plan):
                raise TypeError("plan must be Plan.")
            if self.plan.goal_id != self.request.goal.goal_id:
                raise ValueError("Plan.goal_id does not match PipelineRequest.")
            if self.plan.domain.casefold() != self.request.goal.domain.casefold():
                raise ValueError("Plan.domain does not match PipelineRequest.")
            if self.plan.state_revision != self.request.state.revision:
                raise ValueError("Plan state revision is stale.")

        stages = [result.stage for result in self.stage_results]
        if len(stages) != len(set(stages)):
            raise ValueError("PipelineContext stage_results must be unique.")

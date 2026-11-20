from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping
from enum import Enum

from .contracts import DomainPolicy
from .decision_engine import BeliefState, DecisionCandidate, DecisionResult
from .governance import GovernanceDecision, GovernanceRequest
from .hierarchical_engine import HierarchicalMethod
from .hierarchy import Task
from .multiagent import AgentBid, AgentDescriptor, CoordinationTask, MultiAgentAllocation
from .models import Plan
from .pipeline_contracts import PipelineRequest, PipelineStageResult
from .scheduler import PlanMetrics, ScheduleResult
from .validation import PlanValidationResult
from .world_model import WorldState, RuleBasedWorldModel, WorldPrediction
from .execution import (
    ExecutionSnapshot, ExecutionFeedback, RecoveryPolicy, RecoveryDecision,
)
from .replanning import ReplanDecision
from .metacognition import (
    MetaCognitiveState, OutcomeEvidence, StrategyCandidate, MetaPolicy, MetaDecision,
)


class PipelinePlanningMode(str, Enum):
    HTN = "htn"
    STRATEGY = "strategy"


@dataclass(frozen=True)
class PipelineInputs:
    """Explicit, immutable runtime inputs for optional pipeline stages."""

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

    # World Model: state interpretation is explicit; the core never guesses facts.
    world_state: WorldState | None = None
    world_model: RuleBasedWorldModel | None = None
    world_action: str | None = None

    # Execution monitoring receives externally maintained snapshots/feedback.
    execution_snapshot: ExecutionSnapshot | None = None
    execution_feedback: ExecutionFeedback | None = None

    # Recovery and replanning are recommendation-only.
    recovery_step_id: str | None = None
    recovery_policy: RecoveryPolicy | None = None
    current_world_revision: int | None = None
    changed_fact_keys: tuple[str, ...] = ()
    step_fact_dependencies: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    replan_trigger: str | None = None
    risk_limit_exceeded: bool = False

    # Meta-cognition only learns from verified evidence.
    meta_state: MetaCognitiveState = field(default_factory=MetaCognitiveState)
    meta_candidates: tuple[StrategyCandidate, ...] = ()
    meta_policy: MetaPolicy = field(default_factory=MetaPolicy)
    outcome_evidence: tuple[OutcomeEvidence, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.planning_mode, PipelinePlanningMode):
            raise TypeError("planning_mode must be a PipelinePlanningMode.")

        if self.planning_mode is PipelinePlanningMode.HTN:
            if not self.htn_tasks or not self.htn_methods:
                raise ValueError("HTN mode requires htn_tasks and htn_methods.")
        elif self.htn_tasks or self.htn_methods:
            raise ValueError("HTN inputs must be empty in STRATEGY mode.")

        if (self.belief_state is None) != (not self.decision_candidates):
            raise ValueError("Decision requires both belief_state and decision_candidates.")

        multiagent_values = (bool(self.agents), bool(self.coordination_tasks), bool(self.agent_bids))
        if any(multiagent_values) and not all(multiagent_values):
            raise ValueError("Multi-Agent input requires agents, coordination_tasks and agent_bids.")

        if self.governance_request is not None and not isinstance(self.governance_request, GovernanceRequest):
            raise TypeError("governance_request must be GovernanceRequest.")

        if self.world_state is not None and not isinstance(self.world_state, WorldState):
            raise TypeError("world_state must be WorldState.")
        if self.world_model is not None and not isinstance(self.world_model, RuleBasedWorldModel):
            raise TypeError("world_model must be RuleBasedWorldModel.")
        if self.world_action is not None and (not isinstance(self.world_action, str) or not self.world_action.strip()):
            raise ValueError("world_action must be a non-empty string.")

        if self.execution_snapshot is not None and not isinstance(self.execution_snapshot, ExecutionSnapshot):
            raise TypeError("execution_snapshot must be ExecutionSnapshot.")
        if self.execution_feedback is not None and not isinstance(self.execution_feedback, ExecutionFeedback):
            raise TypeError("execution_feedback must be ExecutionFeedback.")
        if self.recovery_policy is not None and not isinstance(self.recovery_policy, RecoveryPolicy):
            raise TypeError("recovery_policy must be RecoveryPolicy.")
        if self.recovery_step_id is not None and (not isinstance(self.recovery_step_id, str) or not self.recovery_step_id.strip()):
            raise ValueError("recovery_step_id must be a non-empty string.")
        if self.current_world_revision is not None and (
            isinstance(self.current_world_revision, bool)
            or not isinstance(self.current_world_revision, int)
            or self.current_world_revision < 0
        ):
            raise ValueError("current_world_revision must be a non-negative integer.")

        if not isinstance(self.meta_state, MetaCognitiveState):
            raise TypeError("meta_state must be MetaCognitiveState.")
        if not isinstance(self.meta_policy, MetaPolicy):
            raise TypeError("meta_policy must be MetaPolicy.")
        if any(not isinstance(item, StrategyCandidate) for item in self.meta_candidates):
            raise TypeError("meta_candidates must contain StrategyCandidate values.")
        if any(not isinstance(item, OutcomeEvidence) for item in self.outcome_evidence):
            raise TypeError("outcome_evidence must contain OutcomeEvidence values.")

        object.__setattr__(self, "htn_context", MappingProxyType(dict(self.htn_context)))
        object.__setattr__(self, "htn_dependencies", MappingProxyType({
            key: tuple(value) for key, value in self.htn_dependencies.items()
        }))
        object.__setattr__(self, "step_fact_dependencies", MappingProxyType({
            key: tuple(value) for key, value in self.step_fact_dependencies.items()
        }))
        object.__setattr__(self, "changed_fact_keys", tuple(self.changed_fact_keys))
        object.__setattr__(self, "meta_candidates", tuple(self.meta_candidates))
        object.__setattr__(self, "outcome_evidence", tuple(self.outcome_evidence))


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

    world_prediction: WorldPrediction | None = None
    execution_snapshot: ExecutionSnapshot | None = None
    recovery: RecoveryDecision | None = None
    replanning: ReplanDecision | None = None
    meta_state: MetaCognitiveState | None = None
    meta_decision: MetaDecision | None = None

    stage_results: tuple[PipelineStageResult, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.request, PipelineRequest):
            raise TypeError("request must be PipelineRequest.")
        if not isinstance(self.inputs, PipelineInputs):
            raise TypeError("inputs must be PipelineInputs.")

        if self.domain_policy is not None:
            if not isinstance(self.domain_policy, DomainPolicy):
                raise TypeError("domain_policy must be DomainPolicy.")
            if self.domain_policy.domain_id.casefold() != self.request.goal.domain.casefold():
                raise ValueError("DomainPolicy.domain_id must match the request domain.")

        if self.plan is not None:
            if not isinstance(self.plan, Plan):
                raise TypeError("plan must be Plan.")
            if self.plan.goal_id != self.request.goal.goal_id:
                raise ValueError("Plan.goal_id does not match PipelineRequest.")
            if self.plan.domain.casefold() != self.request.goal.domain.casefold():
                raise ValueError("Plan.domain does not match PipelineRequest.")
            if self.plan.state_revision != self.request.state.revision:
                raise ValueError("Plan state revision is stale.")

        if self.world_prediction is not None and not isinstance(self.world_prediction, WorldPrediction):
            raise TypeError("world_prediction must be WorldPrediction.")
        if self.execution_snapshot is not None:
            if not isinstance(self.execution_snapshot, ExecutionSnapshot):
                raise TypeError("execution_snapshot must be ExecutionSnapshot.")
            if self.plan is not None and self.execution_snapshot.plan_id != self.plan.plan_id:
                raise ValueError("ExecutionSnapshot belongs to another plan.")

        stages = [result.stage for result in self.stage_results]
        if len(stages) != len(set(stages)):
            raise ValueError("PipelineContext stage_results must be unique.")

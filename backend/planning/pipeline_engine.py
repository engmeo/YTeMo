"""Domain-neutral orchestration pipeline for Planning components.

This module proposes and evaluates plans. It never executes actions.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable, Mapping

from .pipeline_contracts import (
    PipelineStage,
    StageStatus,
    PipelineStatus,
    StageProvenance,
    PipelineStageResult,
    PipelineResult,
)
from .pipeline_context import PipelineContext, PipelineInputs, PipelinePlanningMode
from .pipeline_adapters import (
    run_htn_adapter,
    run_decision_adapter,
    run_multiagent_allocation_adapter,
)
from .models import Plan
from .validation import validate_plan, mark_validated
from .scheduler import schedule_plan, evaluate_plan
from .governance import evaluate_governance


def _now() -> datetime:
    """Return timezone-aware UTC datetime for pipeline contracts."""
    return datetime.now(timezone.utc)


def _value(value: object) -> str:
    return str(getattr(value, "value", value)).lower()


class PipelineStageRegistry:
    """Deterministic registry of supported pipeline stage handlers."""

    def __init__(self) -> None:
        self._handlers: dict[PipelineStage, Callable] = {}

    def register(self, stage: PipelineStage, handler: Callable, *, replace_existing: bool = False) -> None:
        if not isinstance(stage, PipelineStage):
            raise TypeError("stage must be a PipelineStage")
        if not callable(handler):
            raise TypeError("handler must be callable")
        if stage in self._handlers and not replace_existing:
            raise ValueError(f"Handler already registered for {stage.value}")
        self._handlers[stage] = handler

    def get(self, stage: PipelineStage) -> Callable:
        try:
            return self._handlers[stage]
        except KeyError as exc:
            raise ValueError(f"Unsupported pipeline stage: {stage.value}") from exc

    def supports(self, stage: PipelineStage) -> bool:
        return stage in self._handlers

    @property
    def stages(self) -> tuple[PipelineStage, ...]:
        return tuple(self._handlers)


class PipelineEngine:
    """Compose existing Planning engines behind a single pipeline boundary."""

    ORDER = (
        PipelineStage.INTAKE,
        PipelineStage.HTN_PLANNING,
        PipelineStage.STRATEGY_PLANNING,
        PipelineStage.DECISION,
        PipelineStage.MULTI_AGENT_ALLOCATION,
        PipelineStage.VALIDATION,
        PipelineStage.SCHEDULING,
        PipelineStage.GOVERNANCE,
    )

    def __init__(
        self,
        *,
        registry: PipelineStageRegistry | None = None,
        resource_capacities: Mapping[str, float] | None = None,
        max_parallel_steps: int = 4,
        planning_policy=None,
        decision_policy=None,
        multiagent_policy=None,
        mandatory_human_review_threshold: float = 0.75,
    ) -> None:
        if max_parallel_steps < 1:
            raise ValueError("max_parallel_steps must be positive")
        self.resource_capacities = dict(resource_capacities or {})
        self.max_parallel_steps = max_parallel_steps
        self.planning_policy = planning_policy
        self.decision_policy = decision_policy
        self.multiagent_policy = multiagent_policy
        self.mandatory_human_review_threshold = mandatory_human_review_threshold
        self.registry = registry or PipelineStageRegistry()

        handlers = {
            PipelineStage.INTAKE: self._intake,
            PipelineStage.HTN_PLANNING: self._htn,
            PipelineStage.STRATEGY_PLANNING: self._strategy,
            PipelineStage.DECISION: self._decision,
            PipelineStage.MULTI_AGENT_ALLOCATION: self._allocation,
            PipelineStage.VALIDATION: self._validation,
            PipelineStage.SCHEDULING: self._scheduling,
            PipelineStage.GOVERNANCE: self._governance,
        }
        for stage, handler in handlers.items():
            if not self.registry.supports(stage):
                self.registry.register(stage, handler)

    def _intake(self, context: PipelineContext, strategy=None):
        return context, context.request

    def _htn(self, context: PipelineContext, strategy=None):
        request, inputs = context.request, context.inputs
        result = run_htn_adapter(
            goal=request.goal,
            state=request.state,
            tasks=inputs.htn_tasks,
            methods=inputs.htn_methods,
            context=inputs.htn_context,
            dependencies=inputs.htn_dependencies,
            policy=self.planning_policy,
        )
        return replace(context, plan=result.plan, validation=result.validation), result

    def _strategy(self, context: PipelineContext, strategy=None):
        if strategy is None or not callable(getattr(strategy, "generate_steps", None)):
            raise ValueError("STRATEGY planning requires a PlannerStrategy")
        steps = strategy.generate_steps(context.request.goal, context.request.state)
        plan = Plan.create(context.request.goal, context.request.state, steps)
        return replace(context, plan=plan), plan

    def _decision(self, context: PipelineContext, strategy=None):
        inputs = context.inputs
        if inputs.belief_state is None:
            raise ValueError("Decision stage requires belief_state and decision_candidates")
        result = run_decision_adapter(
            belief=inputs.belief_state,
            candidates=inputs.decision_candidates,
            policy=self.decision_policy,
        )
        return replace(context, decision=result), result

    def _allocation(self, context: PipelineContext, strategy=None):
        inputs = context.inputs
        if not inputs.agents:
            raise ValueError("Multi-Agent stage requires agents, tasks and bids")
        result = run_multiagent_allocation_adapter(
            agents=inputs.agents,
            tasks=inputs.coordination_tasks,
            bids=inputs.agent_bids,
            policy=self.multiagent_policy,
        )
        return replace(context, allocation=result), result

    def _validation(self, context: PipelineContext, strategy=None):
        if context.plan is None:
            raise ValueError("Validation requires a generated Plan")
        result = validate_plan(
            context.plan,
            policy=self.planning_policy,
            domain_policy=context.domain_policy,
        )
        plan = (
            mark_validated(
                context.plan,
                policy=self.planning_policy,
                domain_policy=context.domain_policy,
            )
            if result.valid else context.plan
        )
        return replace(context, plan=plan, validation=result), result

    def _scheduling(self, context: PipelineContext, strategy=None):
        if context.plan is None:
            raise ValueError("Scheduling requires a Plan")
        result = schedule_plan(
            context.plan,
            self.resource_capacities,
            max_parallel_steps=self.max_parallel_steps,
            domain_policy=context.domain_policy,
        )
        metrics = evaluate_plan(context.plan, domain_policy=context.domain_policy)
        return replace(context, schedule=result, metrics=metrics), result

    def _governance(self, context: PipelineContext, strategy=None):
        if context.inputs.governance_request is None:
            raise ValueError("Governance stage requires governance_request")
        result = evaluate_governance(
            context.inputs.governance_request,
            mandatory_human_review_threshold=self.mandatory_human_review_threshold,
        )
        return replace(context, governance=result), result

    def run(self, request, inputs: PipelineInputs, *, strategy=None) -> PipelineResult:
        policy = request.policy
        context = PipelineContext(
            request=request,
            inputs=inputs,
            domain_policy=None,
        )

        enabled = set(request.enabled_stages)
        planning_stage = (
            PipelineStage.HTN_PLANNING
            if inputs.planning_mode == PipelinePlanningMode.HTN
            else PipelineStage.STRATEGY_PLANNING
        )

        mandatory = {
            planning_stage,
            PipelineStage.VALIDATION,
            PipelineStage.SCHEDULING,
        }
        if not mandatory.issubset(enabled):
            missing = sorted(stage.value for stage in mandatory - enabled)
            raise ValueError(f"Request must enable mandatory stages: {missing}")

        if policy.governance_required and PipelineStage.GOVERNANCE not in enabled:
            raise ValueError("Governance is required but not enabled")

        unknown = [stage for stage in enabled if not self.registry.supports(stage)]
        if unknown:
            names = ", ".join(sorted(stage.value for stage in unknown))
            raise ValueError(f"No registered handler for enabled stages: {names}")

        required = set(policy.required_stages) | mandatory
        started = _now()
        stage_results = []
        reasons = []
        failed_required = False
        failed_optional = False
        status = PipelineStatus.SUCCEEDED

        components = {
            PipelineStage.INTAKE: "planning.pipeline_engine.PipelineEngine._intake",
            PipelineStage.HTN_PLANNING: "planning.pipeline_adapters.run_htn_adapter",
            PipelineStage.STRATEGY_PLANNING: "planning.pipeline_engine.PlannerStrategy",
            PipelineStage.DECISION: "planning.decision_engine.select_decision",
            PipelineStage.MULTI_AGENT_ALLOCATION: "planning.multiagent.allocate_tasks",
            PipelineStage.VALIDATION: "planning.validation.validate_plan",
            PipelineStage.SCHEDULING: "planning.scheduler.schedule_plan",
            PipelineStage.GOVERNANCE: "planning.governance.evaluate_governance",
        }

        def make_provenance(stage, handler_name):
            if not policy.require_provenance:
                return None
            return StageProvenance(
                stage=stage,
                component=components.get(stage, f"planning.{stage.value}"),
                component_version=policy.version,
                input_revision=request.state.revision,
                output_revision=request.state.revision,
                evidence_refs=(),
                metadata={
                    "handler": handler_name,
                    "policy_version": policy.version,
                },
            )

        for stage in self.ORDER:
            if stage not in enabled:
                continue

            stage_started = _now()
            handler = self.registry.get(stage)

            try:
                context, output = handler(context, strategy)
                stage_status = StageStatus.SUCCEEDED
                reason = None

                if stage == PipelineStage.VALIDATION and not context.validation.valid:
                    stage_status = StageStatus.BLOCKED
                    reason = "Plan validation failed"
                    status = PipelineStatus.BLOCKED
                    reasons.append(reason)

                elif stage == PipelineStage.SCHEDULING and not context.schedule.feasible:
                    stage_status = StageStatus.BLOCKED
                    reason = "Plan scheduling is infeasible"
                    status = PipelineStatus.BLOCKED
                    reasons.append(reason)

                elif stage == PipelineStage.GOVERNANCE:
                    governance_status = _value(context.governance.status)
                    if governance_status in ("rejected", "denied"):
                        stage_status = StageStatus.BLOCKED
                        reason = "Governance rejected the request"
                        status = PipelineStatus.BLOCKED
                        reasons.append(reason)
                    elif governance_status in ("pending", "human_review", "requires_review"):
                        stage_status = StageStatus.HUMAN_REVIEW
                        reason = "Governance requires human review"
                        status = PipelineStatus.HUMAN_REVIEW
                        reasons.append(reason)

                result = PipelineStageResult(
                    stage=stage,
                    status=stage_status,
                    output=output,
                    provenance=make_provenance(stage, getattr(handler, "__qualname__", type(handler).__name__)),
                    started_at=stage_started,
                    completed_at=_now(),
                    issues=(),
                    reason=reason,
                )
                stage_results.append(result)
                context = replace(context, stage_results=tuple(stage_results))

                # Safety gates always stop the pipeline.
                if stage_status in (StageStatus.BLOCKED, StageStatus.HUMAN_REVIEW):
                    break

            except Exception as exc:
                reason = f"{stage.value}: {type(exc).__name__}: {exc}"
                reasons.append(reason)

                result = PipelineStageResult(
                    stage=stage,
                    status=StageStatus.FAILED,
                    output=None,
                    provenance=make_provenance(
                        stage,
                        getattr(handler, "__qualname__", type(handler).__name__),
                    ),
                    started_at=stage_started,
                    completed_at=_now(),
                    issues=(reason,),
                    reason=str(exc),
                )
                stage_results.append(result)
                context = replace(context, stage_results=tuple(stage_results))

                if stage in required:
                    failed_required = True
                else:
                    failed_optional = True

                # Required-stage failures and disabled partial results are fatal.
                if (
                    stage in required
                    or policy.stop_on_stage_failure
                    or not policy.allow_partial_results
                ):
                    break

        if status not in (PipelineStatus.BLOCKED, PipelineStatus.HUMAN_REVIEW):
            if failed_required or (failed_optional and not policy.allow_partial_results):
                status = PipelineStatus.FAILED
            elif failed_optional:
                status = PipelineStatus.PARTIAL
            elif context.plan is not None and context.plan.status.value == "human_review":
                status = PipelineStatus.HUMAN_REVIEW
            else:
                status = PipelineStatus.SUCCEEDED

        result_plan = context.plan
        if status == PipelineStatus.FAILED and not policy.allow_partial_results:
            result_plan = None

        return PipelineResult(
            request_id=request.request_id,
            goal_id=request.goal.goal_id,
            domain=request.goal.domain,
            status=status,
            stage_results=tuple(stage_results),
            started_at=started,
            completed_at=_now(),
            plan=result_plan,
            reasons=tuple(reasons),
            metadata={
                "planning_mode": inputs.planning_mode.value,
                "executed_stages": tuple(item.stage.value for item in stage_results),
                "execution_performed": False,
                "policy_version": policy.version,
                "allow_partial_results": policy.allow_partial_results,
                "stop_on_stage_failure": policy.stop_on_stage_failure,
            },
        )

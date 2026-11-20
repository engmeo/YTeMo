from planning.models import BeliefHypothesis
from planning.pipeline_engine import PipelineEngine, PipelineStageRegistry
from planning.pipeline_contracts import (
    PipelineStage, PipelinePolicy, PipelineRequest,
)
from planning.pipeline_context import PipelineInputs, PipelinePlanningMode
from planning.models import Goal, StateSnapshot, PlanStep


class SimpleStrategy:
    def generate_steps(self, goal, state):
        return (
            PlanStep(
                step_id="step-1",
                action="analyze",
                description="Analyze the requested goal",
                expected_duration_seconds=1,
            ),
        )


def make_request(stages):
    goal = Goal(
        goal_id="goal-1",
        description="Test planning pipeline",
        domain="general",
    )
    state = StateSnapshot(
        subject_id="subject-1",
        domain="general",
        revision=1,
        as_of="2026-11-20T00:00:00+00:00",
    )
    request = PipelineRequest(
        goal=goal,
        state=state,
        enabled_stages=tuple(stages),
        request_id="request-1",
        policy=PipelinePolicy(),
    )
    return request


def test_registry_has_eight_supported_handlers():
    engine = PipelineEngine()
    assert len(engine.registry.stages) == 8
    assert engine.registry.supports(PipelineStage.STRATEGY_PLANNING)
    assert engine.registry.supports(PipelineStage.GOVERNANCE)


def test_registry_rejects_duplicate_handler():
    registry = PipelineStageRegistry()
    registry.register(PipelineStage.INTAKE, lambda context: context)
    try:
        registry.register(PipelineStage.INTAKE, lambda context: context)
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate handler was accepted")


def test_strategy_pipeline_runs_through_validation_and_scheduling():
    stages = (
        PipelineStage.STRATEGY_PLANNING,
        PipelineStage.VALIDATION,
        PipelineStage.SCHEDULING,
    )
    request = make_request(stages)
    inputs = PipelineInputs(planning_mode=PipelinePlanningMode.STRATEGY)

    result = PipelineEngine().run(
        request,
        inputs,
        strategy=SimpleStrategy(),
    )

    assert result.plan is not None
    assert result.plan.goal_id == "goal-1"
    assert result.status.value == "succeeded", result.reasons
    assert result.plan.status.value in ("validated", "ready")
    assert tuple(item.stage for item in result.stage_results) == stages
    assert all(item.status.value == "succeeded" for item in result.stage_results)
    assert result.metadata["execution_performed"] is False


def test_pipeline_rejects_unsupported_world_model_stage():
    stages = (
        PipelineStage.STRATEGY_PLANNING,
        PipelineStage.WORLD_MODEL,
        PipelineStage.VALIDATION,
        PipelineStage.SCHEDULING,
    )
    request = make_request(stages)
    inputs = PipelineInputs(planning_mode=PipelinePlanningMode.STRATEGY)

    try:
        PipelineEngine().run(request, inputs, strategy=SimpleStrategy())
    except ValueError as exc:
        assert "No registered handler" in str(exc)
    else:
        raise AssertionError("Unsupported stage was silently accepted")


def test_strategy_pipeline_requires_strategy_object():
    stages = (
        PipelineStage.STRATEGY_PLANNING,
        PipelineStage.VALIDATION,
        PipelineStage.SCHEDULING,
    )
    request = make_request(stages)
    inputs = PipelineInputs(planning_mode=PipelinePlanningMode.STRATEGY)

    result = PipelineEngine().run(request, inputs)
    assert result.status.value == "failed"
    assert any("PlannerStrategy" in reason for reason in result.reasons)




# PIPELINE_ENGINE_INTEGRATION_TESTS

from planning.pipeline_contracts import PipelineStage
from planning.pipeline_context import PipelineInputs, PipelinePlanningMode
from planning.pipeline_engine import PipelineEngine
from planning.hierarchical_engine import Task, HierarchicalMethod, DecompositionMethod
from planning.decision_engine import BeliefState, DecisionCandidate
from planning.multiagent import AgentDescriptor, CoordinationTask, AgentBid
from planning.governance import GovernanceRequest


def _integration_stage(result, stage):
    matches = [item for item in result.stage_results if item.stage == stage]
    assert len(matches) == 1, f"Expected exactly one result for {stage}; pipeline_status={result.status}; reasons={result.reasons}; stage_results={result.stage_results}"
    return matches[0]


def test_pipeline_decision_stage_integration():
    stages = (PipelineStage.STRATEGY_PLANNING, PipelineStage.VALIDATION, PipelineStage.SCHEDULING, PipelineStage.DECISION,)
    request = make_request(stages)
    inputs = PipelineInputs(
        planning_mode=PipelinePlanningMode.STRATEGY,
        belief_state=BeliefState(
            snapshot=request.state,
            hypotheses=(
                BeliefHypothesis("h1", "First hypothesis", 0.7),
                BeliefHypothesis("h2", "Second hypothesis", 0.3),
            ),
        ),
        decision_candidates=(
            DecisionCandidate(
                action_id="option-a",
                description="First option",
                utilities={"h1": 0.9, "h2": 0.8},
            ),
            DecisionCandidate(
                action_id="option-b",
                description="Second option",
                utilities={"h1": 0.5, "h2": 0.4},
            ),
        ),
    )

    result = PipelineEngine().run(request, inputs, strategy=SimpleStrategy())
    stage = _integration_stage(result, PipelineStage.DECISION)

    assert stage.status.value == "succeeded", stage.reason
    assert stage.output is not None


def test_pipeline_multiagent_stage_integration():
    stages = (PipelineStage.STRATEGY_PLANNING, PipelineStage.VALIDATION, PipelineStage.SCHEDULING, PipelineStage.MULTI_AGENT_ALLOCATION,)
    request = make_request(stages)
    inputs = PipelineInputs(
        planning_mode=PipelinePlanningMode.STRATEGY,
        agents=(AgentDescriptor("agent-a", ("analysis",)),),
        coordination_tasks=(CoordinationTask("task-a", ("analysis",)),),
        agent_bids=(
            AgentBid(
                agent_id="agent-a",
                task_id="task-a",
                estimated_cost=1.0,
                estimated_duration=1.0,
                confidence=0.95,
            ),
        ),
    )

    result = PipelineEngine().run(request, inputs, strategy=SimpleStrategy())
    stage = _integration_stage(result, PipelineStage.MULTI_AGENT_ALLOCATION)

    assert stage.status.value == "succeeded", stage.reason
    assert stage.output is not None


def test_pipeline_governance_stage_integration():
    stages = (PipelineStage.STRATEGY_PLANNING, PipelineStage.VALIDATION, PipelineStage.SCHEDULING, PipelineStage.GOVERNANCE,)
    request = make_request(stages)
    inputs = PipelineInputs(
        planning_mode=PipelinePlanningMode.STRATEGY,
        governance_request=GovernanceRequest(
            plan_id="goal-1",
            risk_level=0.2,
            consent_granted=True,
            evidence_satisfied=True,
            policy_allowed=True,
        ),
    )

    result = PipelineEngine().run(request, inputs, strategy=SimpleStrategy())
    stage = _integration_stage(result, PipelineStage.GOVERNANCE)

    assert stage.status.value in ("succeeded", "human_review"), stage.reason
    assert stage.output is not None


def test_pipeline_governance_denies_missing_consent():
    stages = (PipelineStage.STRATEGY_PLANNING, PipelineStage.VALIDATION, PipelineStage.SCHEDULING, PipelineStage.GOVERNANCE,)
    request = make_request(stages)
    inputs = PipelineInputs(
        planning_mode=PipelinePlanningMode.STRATEGY,
        governance_request=GovernanceRequest(
            plan_id="goal-1",
            risk_level=0.2,
            consent_granted=False,
        ),
    )

    result = PipelineEngine().run(request, inputs, strategy=SimpleStrategy())
    stage = _integration_stage(result, PipelineStage.GOVERNANCE)

    assert stage.output is not None
    assert stage.output.executable is False


def test_pipeline_decision_missing_input_does_not_succeed():
    stages = (PipelineStage.STRATEGY_PLANNING, PipelineStage.VALIDATION, PipelineStage.SCHEDULING, PipelineStage.DECISION,)
    request = make_request(stages)
    inputs = PipelineInputs(planning_mode=PipelinePlanningMode.STRATEGY)

    result = PipelineEngine().run(request, inputs, strategy=SimpleStrategy())
    stage = _integration_stage(result, PipelineStage.DECISION)

    assert stage.status.value in ("failed", "blocked")
    assert stage.output is None








# PIPELINE_ORCHESTRATION_POLICY_TESTS

def _request_with_policy(stages, policy):
    base = make_request(stages)
    return PipelineRequest(
        goal=base.goal,
        state=base.state,
        enabled_stages=tuple(stages),
        request_id="policy-request",
        policy=policy,
    )


def _failing_intake(context, strategy=None):
    raise RuntimeError("intentional intake failure")


def test_pipeline_policy_continues_after_optional_failure():
    stages = (
        PipelineStage.INTAKE,
        PipelineStage.STRATEGY_PLANNING,
        PipelineStage.VALIDATION,
        PipelineStage.SCHEDULING,
    )
    policy = PipelinePolicy(
        stop_on_stage_failure=False,
        allow_partial_results=True,
    )
    request = _request_with_policy(stages, policy)
    registry = PipelineStageRegistry()
    registry.register(PipelineStage.INTAKE, _failing_intake)

    result = PipelineEngine(registry=registry).run(
        request,
        PipelineInputs(planning_mode=PipelinePlanningMode.STRATEGY),
        strategy=SimpleStrategy(),
    )

    assert result.status.value == "partial"
    assert result.plan is not None
    assert result.metadata["executed_stages"] == tuple(s.value for s in stages)
    assert result.stage_results[0].status.value == "failed"


def test_pipeline_policy_stops_after_optional_failure_when_configured():
    stages = (
        PipelineStage.INTAKE,
        PipelineStage.STRATEGY_PLANNING,
        PipelineStage.VALIDATION,
        PipelineStage.SCHEDULING,
    )
    policy = PipelinePolicy(
        stop_on_stage_failure=True,
        allow_partial_results=True,
    )
    request = _request_with_policy(stages, policy)
    registry = PipelineStageRegistry()
    registry.register(PipelineStage.INTAKE, _failing_intake)

    result = PipelineEngine(registry=registry).run(
        request,
        PipelineInputs(planning_mode=PipelinePlanningMode.STRATEGY),
        strategy=SimpleStrategy(),
    )

    assert result.status.value == "partial"
    assert len(result.stage_results) == 1
    assert result.plan is None


def test_pipeline_policy_rejects_partial_result_when_disabled():
    stages = (
        PipelineStage.INTAKE,
        PipelineStage.STRATEGY_PLANNING,
        PipelineStage.VALIDATION,
        PipelineStage.SCHEDULING,
    )
    policy = PipelinePolicy(
        stop_on_stage_failure=False,
        allow_partial_results=False,
    )
    request = _request_with_policy(stages, policy)
    registry = PipelineStageRegistry()
    registry.register(PipelineStage.INTAKE, _failing_intake)

    result = PipelineEngine(registry=registry).run(
        request,
        PipelineInputs(planning_mode=PipelinePlanningMode.STRATEGY),
        strategy=SimpleStrategy(),
    )

    assert result.status.value == "failed"
    assert len(result.stage_results) == 1
    assert result.plan is None


def test_pipeline_provenance_obeys_policy_version_and_requirement():
    stages = (
        PipelineStage.STRATEGY_PLANNING,
        PipelineStage.VALIDATION,
        PipelineStage.SCHEDULING,
    )
    request = _request_with_policy(
        stages,
        PipelinePolicy(require_provenance=True, version="2.5"),
    )
    result = PipelineEngine().run(
        request,
        PipelineInputs(planning_mode=PipelinePlanningMode.STRATEGY),
        strategy=SimpleStrategy(),
    )

    assert all(item.provenance is not None for item in result.stage_results)
    assert all(item.provenance.component_version == "2.5" for item in result.stage_results)
    assert all(item.provenance.metadata["policy_version"] == "2.5" for item in result.stage_results)

    no_provenance_request = _request_with_policy(
        stages,
        PipelinePolicy(require_provenance=False),
    )
    no_provenance_result = PipelineEngine().run(
        no_provenance_request,
        PipelineInputs(planning_mode=PipelinePlanningMode.STRATEGY),
        strategy=SimpleStrategy(),
    )
    assert all(item.provenance is None for item in no_provenance_result.stage_results)

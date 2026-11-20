import pytest

from planning.contracts import DomainPolicy
from planning.models import Goal, Plan, StateSnapshot
from planning.pipeline_contracts import (
    PipelineRequest,
    PipelineStage,
    PipelineStageResult,
    StageStatus,
)
from planning.pipeline_context import (
    PipelineContext,
    PipelineInputs,
    PipelinePlanningMode,
)


def make_goal(goal_id="goal-1", domain="general"):
    return Goal(
        goal_id=goal_id,
        description="Test planning goal",
        domain=domain,
    )


def make_state(revision=1, domain="general"):
    return StateSnapshot(
        subject_id="subject-1",
        domain=domain,
        revision=revision,
        as_of="2026-11-20T10:00:00+00:00",
    )


def make_request(goal=None, state=None):
    return PipelineRequest(
        goal=goal or make_goal(),
        state=state or make_state(),
        enabled_stages=(PipelineStage.INTAKE,),
    )


def test_strategy_inputs_are_valid():
    inputs = PipelineInputs(
        planning_mode=PipelinePlanningMode.STRATEGY
    )
    assert inputs.planning_mode is PipelinePlanningMode.STRATEGY


def test_htn_requires_tasks_and_methods():
    with pytest.raises(ValueError, match="HTN mode requires"):
        PipelineInputs(
            planning_mode=PipelinePlanningMode.HTN
        )


def test_strategy_rejects_htn_inputs():
    with pytest.raises(ValueError, match="HTN inputs"):
        PipelineInputs(
            planning_mode=PipelinePlanningMode.STRATEGY,
            htn_tasks=(object(),),
        )


def test_decision_requires_belief_and_candidates_together():
    with pytest.raises(ValueError, match="Decision requires both"):
        PipelineInputs(
            planning_mode=PipelinePlanningMode.STRATEGY,
            belief_state=object(),
        )

    with pytest.raises(ValueError, match="Decision requires both"):
        PipelineInputs(
            planning_mode=PipelinePlanningMode.STRATEGY,
            decision_candidates=(object(),),
        )


def test_multiagent_requires_all_three_input_groups():
    with pytest.raises(ValueError, match="Multi-Agent input requires"):
        PipelineInputs(
            planning_mode=PipelinePlanningMode.STRATEGY,
            agents=(object(),),
        )


def test_context_accepts_matching_domain_policy():
    context = PipelineContext(
        request=make_request(),
        inputs=PipelineInputs(PipelinePlanningMode.STRATEGY),
        domain_policy=DomainPolicy("general"),
    )
    assert context.domain_policy.domain_id == "general"


def test_context_rejects_mismatched_domain_policy():
    with pytest.raises(ValueError, match="must match"):
        PipelineContext(
            request=make_request(),
            inputs=PipelineInputs(PipelinePlanningMode.STRATEGY),
            domain_policy=DomainPolicy("healthcare"),
        )


def test_context_rejects_plan_for_another_goal():
    request = make_request()
    other_plan = Plan.create(
        make_goal(goal_id="another-goal"),
        request.state,
        (),
    )

    with pytest.raises(ValueError, match="goal_id"):
        PipelineContext(
            request=request,
            inputs=PipelineInputs(PipelinePlanningMode.STRATEGY),
            plan=other_plan,
        )


def test_context_rejects_stale_plan_revision():
    request = make_request(state=make_state(revision=2))
    stale_plan = Plan.create(
        request.goal,
        make_state(revision=1),
        (),
    )

    with pytest.raises(ValueError, match="stale"):
        PipelineContext(
            request=request,
            inputs=PipelineInputs(PipelinePlanningMode.STRATEGY),
            plan=stale_plan,
        )


def test_context_rejects_duplicate_stage_results():
    stage_result = PipelineStageResult(
        stage=PipelineStage.INTAKE,
        status=StageStatus.SUCCEEDED,
    )

    with pytest.raises(ValueError, match="must be unique"):
        PipelineContext(
            request=make_request(),
            inputs=PipelineInputs(PipelinePlanningMode.STRATEGY),
            stage_results=(stage_result, stage_result),
        )


def test_input_mappings_are_copied_and_read_only():
    original = {"source": "test"}

    inputs = PipelineInputs(
        planning_mode=PipelinePlanningMode.STRATEGY,
        htn_context=original,
    )

    original["source"] = "changed"

    assert inputs.htn_context["source"] == "test"

    with pytest.raises(TypeError):
        inputs.htn_context["source"] = "blocked"



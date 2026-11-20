import unittest
from unittest.mock import Mock, patch

from planning import pipeline_adapters as adapters


class TestHTNAdapter(unittest.TestCase):

    def test_forwards_inputs_and_preserves_conversion_outputs(self):
        goal = object()
        state = object()
        tasks = (object(),)
        methods = (object(),)
        context = {"mode": "test"}
        dependencies = {"task-b": ("task-a",)}
        decomposition = object()
        plan = object()
        validation = object()
        planner = Mock()
        planner.plan.return_value = decomposition

        with patch.object(
            adapters,
            "hierarchical_result_to_plan",
            return_value=(plan, validation),
        ) as converter:
            result = adapters.run_htn_adapter(
                goal=goal,
                state=state,
                tasks=tasks,
                methods=methods,
                context=context,
                dependencies=dependencies,
                planner=planner,
            )

        planner.plan.assert_called_once_with(
            tasks,
            methods,
            context=context,
            dependencies=dependencies,
        )
        converter.assert_called_once_with(
            goal,
            state,
            decomposition,
            task_payload_defaults=None,
            policy=None,
        )

        self.assertIs(result.decomposition, decomposition)
        self.assertIs(result.plan, plan)
        self.assertIs(result.validation, validation)


class TestDecisionAdapter(unittest.TestCase):

    def test_forwards_inputs_and_returns_original_result(self):
        belief = object()
        candidates = (object(), object())
        policy = object()
        predictions = (object(),)
        expected = object()

        with patch.object(
            adapters,
            "select_decision",
            return_value=expected,
        ) as engine:
            result = adapters.run_decision_adapter(
                belief=belief,
                candidates=candidates,
                policy=policy,
                world_predictions=predictions,
                world_revision=7,
                tie_tolerance=1e-8,
            )

        engine.assert_called_once_with(
            belief,
            candidates,
            policy,
            world_predictions=predictions,
            world_revision=7,
            tie_tolerance=1e-8,
        )
        self.assertIs(result, expected)


class TestMultiAgentAdapter(unittest.TestCase):

    def test_default_policy_uses_engine_default(self):
        agents = (object(),)
        tasks = (object(),)
        bids = (object(),)
        expected = object()

        with patch.object(
            adapters,
            "allocate_tasks",
            return_value=expected,
        ) as engine:
            result = adapters.run_multiagent_allocation_adapter(
                agents=agents,
                tasks=tasks,
                bids=bids,
            )

        engine.assert_called_once_with(agents, tasks, bids)
        self.assertIs(result, expected)

    def test_explicit_policy_is_forwarded(self):
        agents = (object(),)
        tasks = (object(),)
        bids = (object(),)
        policy = object()
        expected = object()

        with patch.object(
            adapters,
            "allocate_tasks",
            return_value=expected,
        ) as engine:
            result = adapters.run_multiagent_allocation_adapter(
                agents=agents,
                tasks=tasks,
                bids=bids,
                policy=policy,
            )

        engine.assert_called_once_with(agents, tasks, bids, policy)
        self.assertIs(result, expected)


if __name__ == "__main__":
    unittest.main()


# ============================================================
# Phase 10.4.6 - Real engine integration tests
# ============================================================

class TestHTNAdapterIntegration(unittest.TestCase):

    def test_real_htn_engine_creates_valid_plan(self):
        from planning.hierarchy import Task, DecompositionMethod
        from planning.models import Goal, StateSnapshot

        goal = Goal(
            goal_id="integration-goal",
            description="Complete mission",
            domain="general",
        )
        state = StateSnapshot(
            subject_id="integration-subject",
            domain="general",
            revision=7,
            as_of="2026-11-20T00:00:00+00:00",
        )

        result = adapters.run_htn_adapter(
            goal=goal,
            state=state,
            tasks=(Task("root", "mission"),),
            methods=(
                DecompositionMethod(
                    "method-1",
                    "mission",
                    (
                        Task("sense", "sense", True, {"description": "Sense"}),
                        Task("move", "move", True, {"action": "move_robot"}),
                    ),
                ),
            ),
            dependencies={"move": ("sense",)},
        )

        self.assertTrue(result.validation.valid)
        self.assertEqual(result.plan.goal_id, goal.goal_id)
        self.assertEqual(result.plan.state_revision, state.revision)
        self.assertEqual(result.plan.steps[1].depends_on, ("sense",))
        self.assertEqual(result.plan.steps[1].action, "move_robot")

        trace = result.plan.metadata["hierarchical_planning"]["decomposition_trace"]
        self.assertEqual(trace[0]["parent_task_id"], "root")
        self.assertEqual(trace[0]["method_id"], "method-1")


class TestDecisionAdapterIntegration(unittest.TestCase):

    def test_real_decision_engine_selects_feasible_candidate(self):
        from planning.decision_engine import (
            DecisionCandidate,
            DecisionStatus,
        )
        from test_planning_decision_evaluation import make_belief

        result = adapters.run_decision_adapter(
            belief=make_belief(),
            candidates=(
                DecisionCandidate(
                    "integration-action",
                    "Integration action",
                    {"h0": 10, "h1": 0},
                    preconditions_satisfied=True,
                ),
            ),
        )

        self.assertEqual(result.status, DecisionStatus.SELECTED)
        self.assertEqual(result.selected_action_id, "integration-action")
        self.assertEqual(
            result.trace.selected_action_id,
            "integration-action",
        )


class TestMultiAgentAdapterIntegration(unittest.TestCase):

    def test_real_allocator_assigns_capable_agent(self):
        from planning.multiagent import (
            AgentBid,
            AgentDescriptor,
            AllocationStatus,
            CoordinationTask,
        )

        result = adapters.run_multiagent_allocation_adapter(
            agents=(
                AgentDescriptor("agent-python", ("python",)),
                AgentDescriptor("agent-java", ("java",)),
            ),
            tasks=(
                CoordinationTask(
                    "integration-task",
                    required_capabilities=("python",),
                ),
            ),
            bids=(
                AgentBid("agent-python", "integration-task", 1, 1, 0.9),
                AgentBid("agent-java", "integration-task", 1, 1, 0.9),
            ),
        )

        self.assertEqual(result.status, AllocationStatus.COMPLETE)
        self.assertEqual(len(result.assignments), 1)
        self.assertEqual(result.assignments[0].agent_id, "agent-python")
        self.assertEqual(
            result.trace.allocation_order,
            ("integration-task",),
        )

    def test_real_allocator_preserves_safety_conflict_trace(self):
        from planning.multiagent import (
            AgentBid,
            AgentDescriptor,
            CoordinationTask,
        )

        result = adapters.run_multiagent_allocation_adapter(
            agents=(
                AgentDescriptor("unsafe-agent", ("python",)),
                AgentDescriptor("safe-agent", ("python",)),
            ),
            tasks=(CoordinationTask("safety-task", ("python",)),),
            bids=(
                AgentBid(
                    "unsafe-agent",
                    "safety-task",
                    1,
                    1,
                    0.9,
                    safety_eligible=False,
                ),
                AgentBid(
                    "safe-agent",
                    "safety-task",
                    1,
                    1,
                    0.9,
                ),
            ),
        )

        self.assertEqual(result.assignments[0].agent_id, "safe-agent")

        rejected = next(
            item
            for item in result.trace.bid_assessments
            if item.agent_id == "unsafe-agent"
        )

        self.assertFalse(rejected.eligible)
        self.assertIn(
            "excluded_by_external_safety_gate",
            rejected.reasons,
        )

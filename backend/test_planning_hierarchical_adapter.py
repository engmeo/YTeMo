import unittest

from planning.hierarchy import Task, DecompositionMethod
from planning.hierarchical_engine import HierarchicalPlanner
from planning.hierarchical_adapter import hierarchical_result_to_plan
from planning.models import Goal, StateSnapshot, StepRisk


class HierarchicalAdapterTests(unittest.TestCase):
    def setUp(self):
        self.goal = Goal(
            goal_id="goal-1",
            description="Complete mission",
            domain="general",
        )
        self.state = StateSnapshot(
            subject_id="subject-1",
            domain="general",
            revision=7,
            as_of="2026-11-20T00:00:00+00:00",
        )

    def test_converts_htn_to_core_plan(self):
        result = HierarchicalPlanner().plan(
            [Task("root", "mission")],
            [
                DecompositionMethod(
                    "m1",
                    "mission",
                    (
                        Task("a", "sense", True, {"description": "Sense"}),
                        Task("b", "move", True, {"action": "move_robot"}),
                    ),
                )
            ],
            dependencies={"b": ["a"]},
        )
        plan, validation = hierarchical_result_to_plan(
            self.goal, self.state, result
        )

        self.assertTrue(validation.valid)
        self.assertEqual(plan.goal_id, "goal-1")
        self.assertEqual(plan.state_revision, 7)
        self.assertEqual(plan.steps[1].depends_on, ("a",))
        self.assertEqual(plan.steps[1].action, "move_robot")

    def test_preserves_decomposition_trace(self):
        result = HierarchicalPlanner().plan(
            [Task("root", "mission")],
            [
                DecompositionMethod(
                    "m1", "mission", (Task("a", "sense", True),)
                )
            ],
        )
        plan, _ = hierarchical_result_to_plan(
            self.goal, self.state, result
        )
        trace = plan.metadata["hierarchical_planning"]["decomposition_trace"]
        self.assertEqual(trace[0]["parent_task_id"], "root")
        self.assertEqual(trace[0]["method_id"], "m1")

    def test_invalid_risk_rejected(self):
        result = HierarchicalPlanner().plan(
            [Task("root", "mission")],
            [
                DecompositionMethod(
                    "m1",
                    "mission",
                    (Task("a", "sense", True, {"risk": "unknown"}),),
                )
            ],
        )
        with self.assertRaises(ValueError):
            hierarchical_result_to_plan(self.goal, self.state, result)

    def test_domain_mismatch_rejected(self):
        result = HierarchicalPlanner().plan(
            [Task("a", "sense", True)], []
        )
        other_goal = Goal(
            goal_id="g2", description="Other", domain="robotics"
        )
        with self.assertRaises(ValueError):
            hierarchical_result_to_plan(other_goal, self.state, result)

    def test_high_risk_requires_human_approval(self):
        result = HierarchicalPlanner().plan(
            [Task("root", "mission")],
            [
                DecompositionMethod(
                    "m1",
                    "mission",
                    (
                        Task(
                            "a", "sensitive_action", True,
                            {"risk": "high"},
                        ),
                    ),
                )
            ],
        )
        plan, validation = hierarchical_result_to_plan(
            self.goal, self.state, result
        )
        self.assertFalse(validation.valid)
        self.assertTrue(validation.blocking_issues)


if __name__ == "__main__":
    unittest.main()

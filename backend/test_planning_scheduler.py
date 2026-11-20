import unittest
from datetime import datetime, timezone

from planning.models import Plan, PlanStep, StepRisk
from planning.scheduler import evaluate_plan, schedule_plan


NOW = datetime.now(timezone.utc).isoformat()


def make_plan(steps):
    return Plan(
        plan_id="plan-1",
        goal_id="goal-1",
        domain="generic",
        state_revision=1,
        steps=tuple(steps),
        created_at=NOW,
    )


class DeterministicSchedulerTests(unittest.TestCase):
    def test_independent_steps_run_in_parallel_within_capacity(self):
        plan = make_plan([
            PlanStep("a", "a", "A", expected_duration_seconds=5, resource_requirements={"cpu": 1}),
            PlanStep("b", "b", "B", expected_duration_seconds=3, resource_requirements={"cpu": 1}),
        ])
        result = schedule_plan(plan, {"cpu": 2}, max_parallel_steps=2)
        self.assertTrue(result.feasible)
        self.assertEqual(
            [(s.step_id, s.start_seconds, s.finish_seconds) for s in result.steps],
            [("a", 0, 5), ("b", 0, 3)],
        )
        self.assertEqual(result.makespan_seconds, 5)

    def test_shared_resource_serializes_steps(self):
        plan = make_plan([
            PlanStep("a", "a", "A", expected_duration_seconds=5, resource_requirements={"gpu": 1}),
            PlanStep("b", "b", "B", expected_duration_seconds=3, resource_requirements={"gpu": 1}),
        ])
        result = schedule_plan(plan, {"gpu": 1}, max_parallel_steps=2)
        self.assertTrue(result.feasible)
        by_id = result.by_step_id
        self.assertEqual((by_id["a"].start_seconds, by_id["a"].finish_seconds), (0, 5))
        self.assertEqual((by_id["b"].start_seconds, by_id["b"].finish_seconds), (5, 8))
        self.assertEqual(result.makespan_seconds, 8)

    def test_dependency_starts_after_predecessor_finishes(self):
        plan = make_plan([
            PlanStep("b", "b", "B", depends_on=("a",), expected_duration_seconds=2),
            PlanStep("a", "a", "A", expected_duration_seconds=4),
        ])
        result = schedule_plan(plan)
        self.assertTrue(result.feasible)
        by_id = result.by_step_id
        self.assertEqual(by_id["a"].start_seconds, 0)
        self.assertEqual(by_id["b"].start_seconds, 4)
        self.assertEqual(result.makespan_seconds, 6)

    def test_independent_resource_fit_is_not_blocked_by_other_ready_step(self):
        plan = make_plan([
            PlanStep("a", "a", "A", expected_duration_seconds=5, resource_requirements={"gpu": 1}),
            PlanStep("b", "b", "B", expected_duration_seconds=2, resource_requirements={"cpu": 1}),
        ])
        result = schedule_plan(plan, {"gpu": 1, "cpu": 1}, max_parallel_steps=2)
        self.assertTrue(result.feasible)
        self.assertEqual(result.by_step_id["a"].start_seconds, 0)
        self.assertEqual(result.by_step_id["b"].start_seconds, 0)


    def test_final_completion_is_not_reported_as_deadlock(self):
        result = schedule_plan(make_plan([
            PlanStep("only", "work", "Only step", expected_duration_seconds=1),
        ]))
        self.assertTrue(result.feasible)
        self.assertEqual(result.issues, ())
        self.assertEqual(result.makespan_seconds, 1)


    def test_missing_duration_is_reported(self):
        result = schedule_plan(make_plan([PlanStep("a", "a", "A")]))
        self.assertFalse(result.feasible)
        self.assertIn("missing_duration", {issue.code for issue in result.issues})

    def test_unknown_resource_is_reported(self):
        plan = make_plan([
            PlanStep("a", "a", "A", expected_duration_seconds=1, resource_requirements={"gpu": 1}),
        ])
        result = schedule_plan(plan, {})
        self.assertFalse(result.feasible)
        self.assertIn("unknown_resource", {issue.code for issue in result.issues})

    def test_resource_demand_over_capacity_is_reported(self):
        plan = make_plan([
            PlanStep("a", "a", "A", expected_duration_seconds=1, resource_requirements={"gpu": 2}),
        ])
        result = schedule_plan(plan, {"gpu": 1})
        self.assertFalse(result.feasible)
        self.assertIn("resource_demand_exceeds_capacity", {issue.code for issue in result.issues})

    def test_invalid_capacity_is_rejected(self):
        for capacity in (-1, float("nan"), float("inf"), True):
            with self.subTest(capacity=capacity), self.assertRaises(ValueError):
                schedule_plan(make_plan([]), {"cpu": capacity})

    def test_parallel_limit_is_enforced(self):
        plan = make_plan([
            PlanStep(name, name, name, expected_duration_seconds=2)
            for name in ("a", "b", "c")
        ])
        result = schedule_plan(plan, max_parallel_steps=2)
        self.assertTrue(result.feasible)
        self.assertEqual(result.by_step_id["a"].start_seconds, 0)
        self.assertEqual(result.by_step_id["b"].start_seconds, 0)
        self.assertEqual(result.by_step_id["c"].start_seconds, 2)

    def test_zero_duration_steps_do_not_deadlock(self):
        plan = make_plan([
            PlanStep("a", "a", "A", expected_duration_seconds=0),
            PlanStep("b", "b", "B", depends_on=("a",), expected_duration_seconds=1),
        ])
        result = schedule_plan(plan)
        self.assertTrue(result.feasible)
        self.assertEqual(result.by_step_id["b"].start_seconds, 0)
        self.assertEqual(result.makespan_seconds, 1)

    def test_high_risk_human_gate_is_preserved_in_schedule(self):
        plan = make_plan([
            PlanStep(
                "review", "review", "Clinician review",
                expected_duration_seconds=10,
                risk=StepRisk.HIGH,
                requires_human_approval=True,
            ),
        ])
        result = schedule_plan(plan)
        self.assertTrue(result.feasible)
        self.assertTrue(result.by_step_id["review"].requires_human_approval)

    def test_invalid_plan_is_not_scheduled(self):
        plan = make_plan([
            PlanStep("a", "a", "A", depends_on=("missing",), expected_duration_seconds=1),
        ])
        result = schedule_plan(plan)
        self.assertFalse(result.feasible)
        self.assertIn("unknown_dependency", {issue.code for issue in result.issues})


class PlanEvaluationTests(unittest.TestCase):
    def test_metrics_include_work_and_critical_path(self):
        plan = make_plan([
            PlanStep("a", "a", "A", expected_duration_seconds=5),
            PlanStep("b", "b", "B", expected_duration_seconds=3),
            PlanStep("c", "c", "C", depends_on=("a",), expected_duration_seconds=4),
        ])
        metrics = evaluate_plan(plan)
        self.assertEqual(metrics.step_count, 3)
        self.assertEqual(metrics.total_work_seconds, 12)
        self.assertEqual(metrics.critical_path_seconds, 9)
        self.assertTrue(metrics.duration_complete)

    def test_unknown_duration_is_reported_without_inventing_estimate(self):
        plan = make_plan([
            PlanStep("a", "a", "A", expected_duration_seconds=5),
            PlanStep("b", "b", "B"),
        ])
        metrics = evaluate_plan(plan)
        self.assertFalse(metrics.duration_complete)
        self.assertIsNone(metrics.total_work_seconds)
        self.assertIsNone(metrics.critical_path_seconds)

    def test_risk_and_approval_counts_are_transparent(self):
        plan = make_plan([
            PlanStep("a", "a", "A", expected_duration_seconds=1, risk=StepRisk.HIGH, requires_human_approval=True),
            PlanStep("b", "b", "B", expected_duration_seconds=1, risk=StepRisk.CRITICAL, requires_human_approval=True),
        ])
        metrics = evaluate_plan(plan)
        self.assertEqual(metrics.high_risk_step_count, 1)
        self.assertEqual(metrics.critical_risk_step_count, 1)
        self.assertEqual(metrics.human_approval_step_count, 2)


if __name__ == "__main__":
    unittest.main()
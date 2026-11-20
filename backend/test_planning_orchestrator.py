import unittest

from planning.models import (
    Goal,
    GoalPriority,
    PlanStatus,
    PlanStep,
    StateSnapshot,
    StepRisk,
)
from planning.orchestrator import PlanningOrchestrator


class SimpleStrategy:
    def generate_steps(self, goal, state):
        return (
            PlanStep(
                step_id="step-1",
                action="collect_information",
                description="Collect required information",
                depends_on=(),
                preconditions=(),
                effects={"information_collected": True},
                risk=StepRisk.LOW,
                requires_human_approval=False,
                expected_duration_seconds=10,
                resource_requirements={},
                evidence_refs=(),
                metadata={},
            ),
        )


class InvalidStrategy:
    def generate_steps(self, goal, state):
        return (
            PlanStep(
                step_id="step-1",
                action="invalid",
                description="Invalid dependency",
                depends_on=("missing-step",),
                preconditions=(),
                effects={},
                risk=StepRisk.LOW,
                requires_human_approval=False,
                expected_duration_seconds=10,
                resource_requirements={},
                evidence_refs=(),
                metadata={},
            ),
        )


def make_inputs():
    goal = Goal(
        goal_id="goal-1",
        description="Complete a generic task",
        domain="general",
        priority=GoalPriority.NORMAL,
        success_criteria=("task completed",),
        constraints=(),
        deadline=None,
        parent_goal_id=None,
        metadata={},
    )
    state = StateSnapshot(
        subject_id="subject-1",
        domain="general",
        revision=1,
        as_of="2026-11-20T00:00:00Z",
        facts=(),
        constraints=(),
        unknowns=(),
    )
    return goal, state


class PlanningOrchestratorTests(unittest.TestCase):
    def test_valid_plan_becomes_ready_without_execution(self):
        goal, state = make_inputs()
        result = PlanningOrchestrator().plan(
            goal, state, SimpleStrategy()
        )

        self.assertEqual(result.status, PlanStatus.READY)
        self.assertEqual(result.plan.status, PlanStatus.READY)
        self.assertTrue(result.validation.valid)
        self.assertIsNotNone(result.schedule)
        self.assertTrue(result.schedule.feasible)
        self.assertIsNotNone(result.metrics)
        self.assertTrue(result.accepted)

    def test_invalid_plan_is_blocked(self):
        goal, state = make_inputs()
        result = PlanningOrchestrator().plan(
            goal, state, InvalidStrategy()
        )

        self.assertEqual(result.status, PlanStatus.BLOCKED)
        self.assertFalse(result.validation.valid)
        self.assertIsNone(result.schedule)
        self.assertFalse(result.accepted)

    def test_domain_mismatch_is_rejected(self):
        goal, state = make_inputs()
        other_state = StateSnapshot(
            subject_id=state.subject_id,
            domain="robotics",
            revision=state.revision,
            as_of=state.as_of,
            facts=(),
            constraints=(),
            unknowns=(),
        )
        with self.assertRaises(ValueError):
            PlanningOrchestrator().plan(
                goal, other_state, SimpleStrategy()
            )


if __name__ == "__main__":
    unittest.main()

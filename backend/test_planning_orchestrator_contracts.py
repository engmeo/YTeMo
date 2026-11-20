import unittest

from planning.contracts import DomainPolicy
from planning.models import (
    Goal,
    GoalPriority,
    PlanStatus,
    PlanStep,
    StateSnapshot,
    StepRisk,
)
from planning.orchestrator import PlanningOrchestrator


class PolicyAdapter:
    def __init__(self, policy):
        self.policy = policy

    def get_policy(self):
        return self.policy


class ApprovalStrategy:
    def generate_steps(self, goal, state):
        return (
            PlanStep(
                step_id="approval-step",
                action="review",
                description="Requires human review",
                depends_on=(),
                preconditions=(),
                effects={},
                risk=StepRisk.HIGH,
                requires_human_approval=True,
                expected_duration_seconds=10,
                resource_requirements={},
                evidence_refs=(),
                metadata={},
            ),
        )


class HighRiskStrategy:
    def generate_steps(self, goal, state):
        return (
            PlanStep(
                step_id="high-risk-step",
                action="sensitive_action",
                description="High risk without approval",
                depends_on=(),
                preconditions=(),
                effects={},
                risk=StepRisk.HIGH,
                requires_human_approval=False,
                expected_duration_seconds=10,
                resource_requirements={},
                evidence_refs=(),
                metadata={},
            ),
        )


def make_inputs():
    goal = Goal(
        goal_id="goal-policy",
        description="Test domain policy",
        domain="general",
        priority=GoalPriority.NORMAL,
        success_criteria=("reviewed",),
        constraints=(),
        deadline=None,
        parent_goal_id=None,
        metadata={},
    )
    state = StateSnapshot(
        subject_id="subject-policy",
        domain="general",
        revision=1,
        as_of="2026-11-20T00:00:00Z",
        facts=(),
        constraints=(),
        unknowns=(),
    )
    return goal, state


class OrchestratorContractTests(unittest.TestCase):
    def test_human_approval_plan_is_not_marked_ready(self):
        goal, state = make_inputs()
        result = PlanningOrchestrator().plan(
            goal, state, ApprovalStrategy()
        )
        self.assertTrue(result.validation.valid)
        self.assertEqual(result.status, PlanStatus.HUMAN_REVIEW)
        self.assertTrue(result.requires_human_review)
        self.assertTrue(result.accepted)

    def test_domain_policy_can_require_human_approval(self):
        goal, state = make_inputs()
        adapter = PolicyAdapter(
            DomainPolicy(
                domain_id="general",
                required_human_approval_risks=frozenset({StepRisk.HIGH}),
            )
        )
        result = PlanningOrchestrator(
            domain_adapter=adapter
        ).plan(goal, state, HighRiskStrategy())

        self.assertFalse(result.validation.valid)
        self.assertEqual(result.status, PlanStatus.BLOCKED)

    def test_adapter_domain_mismatch_is_rejected(self):
        goal, state = make_inputs()
        adapter = PolicyAdapter(
            DomainPolicy(domain_id="robotics")
        )
        with self.assertRaises(ValueError):
            PlanningOrchestrator(
                domain_adapter=adapter
            ).plan(goal, state, ApprovalStrategy())


if __name__ == "__main__":
    unittest.main()

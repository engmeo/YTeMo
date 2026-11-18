import unittest

from agent_foundation import (
    AgentResult,
    AgentTask,
    CriticFeedback,
    CriticVerdict,
    MultiAgentWorkflow,
    SpecialistRunner,
    WorkflowStatus,
    WorkflowStep,
)


class DemoSpecialist:
    name = "DemoSpecialist"

    def __init__(self):
        self.calls = 0

    def execute(self, task, previous_feedback):
        self.calls += 1
        return AgentResult(
            agent_name=self.name,
            status="draft",
            findings=[{"finding": "demo"}],
            output={"revision": self.calls, "feedback_count": len(previous_feedback)},
        )


class ApprovingCritic:
    name = "EvidenceCritic"

    def review(self, task, result):
        return CriticFeedback(self.name, CriticVerdict.APPROVE, rationale="Demo approval")


class RevisingCritic:
    name = "QualityCritic"

    def __init__(self):
        self.calls = 0

    def review(self, task, result):
        self.calls += 1
        if self.calls == 1:
            return CriticFeedback(
                self.name, CriticVerdict.REVISE,
                issues=("Add missing scope limitation",),
            )
        return CriticFeedback(self.name, CriticVerdict.APPROVE)


class BlockingCritic:
    name = "SafetyCritic"

    def review(self, task, result):
        return CriticFeedback(
            self.name, CriticVerdict.BLOCK,
            issues=("Unsafe action requested",),
        )


class HumanReviewCritic:
    name = "ClinicalCritic"

    def review(self, task, result):
        return CriticFeedback(
            self.name, CriticVerdict.HUMAN_REVIEW,
            issues=("Requires clinician review",),
        )


class AgentFoundationTests(unittest.TestCase):
    def setUp(self):
        self.task = AgentTask("test-1", "Test workflow")

    def test_all_critics_approve(self):
        specialist = DemoSpecialist()
        runner = SpecialistRunner(specialist, [ApprovingCritic()])
        report = runner.run(self.task)
        self.assertEqual(report.status, WorkflowStatus.VERIFIED)
        self.assertEqual(report.attempts, 1)

    def test_revision_then_approval(self):
        specialist = DemoSpecialist()
        critic = RevisingCritic()
        runner = SpecialistRunner(specialist, [critic], max_attempts=3)
        report = runner.run(self.task)
        self.assertEqual(report.status, WorkflowStatus.VERIFIED)
        self.assertEqual(report.attempts, 2)
        self.assertEqual(specialist.calls, 2)
        self.assertEqual(report.result.output["feedback_count"], 1)

    def test_block_stops_immediately(self):
        runner = SpecialistRunner(DemoSpecialist(), [BlockingCritic()])
        report = runner.run(self.task)
        self.assertEqual(report.status, WorkflowStatus.BLOCKED)
        self.assertEqual(report.attempts, 1)

    def test_human_review_stops_immediately(self):
        runner = SpecialistRunner(DemoSpecialist(), [HumanReviewCritic()])
        report = runner.run(self.task)
        self.assertEqual(report.status, WorkflowStatus.HUMAN_REVIEW)

    def test_max_attempts_fails_closed(self):
        class AlwaysRevise:
            name = "AlwaysRevise"
            def review(self, task, result):
                return CriticFeedback(self.name, CriticVerdict.REVISE, issues=("Still incomplete",))

        runner = SpecialistRunner(DemoSpecialist(), [AlwaysRevise()], max_attempts=2)
        report = runner.run(self.task)
        self.assertEqual(report.status, WorkflowStatus.REVISION_REQUIRED)
        self.assertEqual(report.attempts, 2)

    def test_workflow_stops_when_step_not_verified(self):
        first = SpecialistRunner(DemoSpecialist(), [BlockingCritic()])
        second_specialist = DemoSpecialist()
        second = SpecialistRunner(second_specialist, [ApprovingCritic()])
        workflow = MultiAgentWorkflow([
            WorkflowStep("first", first),
            WorkflowStep("second", second),
        ])
        report = workflow.run(self.task)
        self.assertEqual(report.status, WorkflowStatus.BLOCKED)
        self.assertEqual(report.stopped_at, "first")
        self.assertEqual(second_specialist.calls, 0)

    def test_workflow_passes_verified_outputs_forward(self):
        class ContextSpecialist(DemoSpecialist):
            name = "ContextSpecialist"
            def execute(self, task, previous_feedback):
                self.calls += 1
                return AgentResult(
                    agent_name=self.name,
                    status="draft",
                    output={"prior": task.context.get("verified_prior_outputs", {})},
                )

        first_agent = DemoSpecialist()
        second_agent = ContextSpecialist()
        workflow = MultiAgentWorkflow([
            WorkflowStep("intake", SpecialistRunner(first_agent, [ApprovingCritic()])),
            WorkflowStep("analysis", SpecialistRunner(second_agent, [ApprovingCritic()])),
        ])
        report = workflow.run(self.task)
        self.assertEqual(report.status, WorkflowStatus.VERIFIED)
        self.assertIn("intake", report.outputs["analysis"].output["prior"])

    def test_duplicate_critic_names_rejected(self):
        class DuplicateCritic:
            name = "same"
            def review(self, task, result):
                return CriticFeedback(self.name, CriticVerdict.APPROVE)
        with self.assertRaises(ValueError):
            SpecialistRunner(DemoSpecialist(), [DuplicateCritic(), DuplicateCritic()])


if __name__ == "__main__":
    unittest.main()

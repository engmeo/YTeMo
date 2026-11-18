import unittest

from agent_foundation import (
    AgentResult,
    CriticFeedback,
    CriticVerdict,
    AgentTask,
    WorkflowStatus,
)
from agent_registry import AgentProfile, AgentRegistry


class FakeSpecialist:
    def __init__(self, name):
        self.name = name

    def execute(self, task, previous_feedback):
        return AgentResult(
            agent_name=self.name,
            status="draft",
            output={"profile": self.name, "goal": task.goal},
        )


class FakeCritic:
    def __init__(self, name, verdict=CriticVerdict.APPROVE):
        self.name = name
        self.verdict = verdict

    def review(self, task, result):
        return CriticFeedback(
            critic_name=self.name,
            verdict=self.verdict,
            rationale="Deterministic test reviewer",
        )


def profile(key, specialist_name=None, critic_name=None, verdict=CriticVerdict.APPROVE):
    specialist_name = specialist_name or f"{key}_specialist"
    critic_name = critic_name or f"{key}_critic"
    return AgentProfile(
        key=key,
        specialist=FakeSpecialist(specialist_name),
        critics=(FakeCritic(critic_name, verdict),),
    )


class AgentRegistryTests(unittest.TestCase):
    def test_register_and_lookup(self):
        registry = AgentRegistry()
        registry.register(profile("intake"))
        self.assertEqual(registry.keys(), ("intake",))
        self.assertEqual(registry.get("intake").specialist.name, "intake_specialist")

    def test_duplicate_profile_rejected(self):
        registry = AgentRegistry()
        registry.register(profile("intake"))
        with self.assertRaises(ValueError):
            registry.register(profile("intake", "another_specialist", "another_critic"))

    def test_unknown_profile_rejected(self):
        with self.assertRaises(KeyError):
            AgentRegistry().get("missing")

    def test_profile_requires_critic(self):
        with self.assertRaises(ValueError):
            AgentProfile("empty", FakeSpecialist("s"), ())

    def test_required_critic_must_be_registered(self):
        with self.assertRaises(ValueError):
            AgentProfile(
                "bad",
                FakeSpecialist("s"),
                (FakeCritic("reviewer"),),
                required_critic_names=("not_registered",),
            )

    def test_build_workflow_and_run(self):
        registry = AgentRegistry()
        registry.register(profile("intake"))
        registry.register(profile("navigation"))
        workflow = registry.build_workflow(("intake", "navigation"))
        report = workflow.run(AgentTask("t-1", "Tìm hiểu nhu cầu"))
        self.assertEqual(report.status, WorkflowStatus.VERIFIED)
        self.assertEqual(tuple(report.outputs.keys()), ("intake", "navigation"))
        self.assertEqual(
            report.outputs["navigation"].output["goal"],
            "Tìm hiểu nhu cầu",
        )

    def test_workflow_stops_on_critic_block(self):
        registry = AgentRegistry()
        registry.register(profile("intake", verdict=CriticVerdict.BLOCK))
        registry.register(profile("navigation"))
        report = registry.build_workflow(("intake", "navigation")).run(
            AgentTask("t-2", "Mục tiêu kiểm thử")
        )
        self.assertEqual(report.status, WorkflowStatus.BLOCKED)
        self.assertEqual(report.stopped_at, "intake")
        self.assertNotIn("navigation", report.outputs)

    def test_duplicate_profile_in_workflow_rejected(self):
        registry = AgentRegistry()
        registry.register(profile("intake"))
        with self.assertRaises(ValueError):
            registry.build_workflow(("intake", "intake"))


if __name__ == "__main__":
    unittest.main()

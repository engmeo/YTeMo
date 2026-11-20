import unittest
from datetime import datetime, timezone
from math import nan, inf

from planning.models import (
    BeliefHypothesis, BeliefState, Goal, GoalPriority, Plan, PlanStep,
    StateFact, StateSnapshot, StepRisk,
)
from planning.validation import PlanningPolicy, mark_validated, validate_plan
from planning.domains.healthcare import HealthcareDomainAdapter
from planning.domains.robotics import RoboticsDomainAdapter


NOW = datetime.now(timezone.utc).isoformat()


def state(domain="generic"):
    return StateSnapshot(
        subject_id="subject-1",
        domain=domain,
        revision=3,
        as_of=NOW,
        facts=(
            StateFact(
                key="location",
                value="Hanoi",
                observed_at=NOW,
                source_type="user",
                source_id="conversation-1",
                confidence=0.95,
            ),
        ),
    )


def goal(domain="generic"):
    return Goal(
        goal_id="goal-1",
        description="Reach the target state",
        domain=domain,
        priority=GoalPriority.HIGH,
        success_criteria=("target_state_reached",),
    )


class PlanningModelTests(unittest.TestCase):
    def test_state_fact_requires_timezone(self):
        with self.assertRaises(ValueError):
            StateFact("x", 1, "2026-01-01T10:00:00", "user", "source")

    def test_state_snapshot_rejects_duplicate_fact_keys(self):
        fact = StateFact("x", 1, NOW, "user", "a")
        with self.assertRaises(ValueError):
            StateSnapshot("s", "generic", 1, NOW, facts=(fact, fact))

    def test_belief_state_distinguishes_known_from_uncertain(self):
        belief = BeliefState(
            snapshot=state(),
            hypotheses=(BeliefHypothesis("h1", "Possible explanation", 0.55),),
            confidence_threshold=0.8,
        )
        self.assertTrue(belief.is_known("location"))
        self.assertFalse(belief.is_known("missing"))
        self.assertEqual(belief.hypotheses[0].probability, 0.55)

    def test_plan_factory_binds_goal_and_state_revision(self):
        item = Plan.create(goal(), state(), (PlanStep("s1", "observe", "Observe current state"),))
        self.assertEqual(item.goal_id, "goal-1")
        self.assertEqual(item.state_revision, 3)
        self.assertEqual(item.domain, "generic")

    def test_plan_factory_rejects_cross_domain_state(self):
        with self.assertRaisesRegex(ValueError, "domain"):
            Plan.create(goal("healthcare"), state("generic"), ())

    def test_nan_and_infinity_are_rejected(self):
        for value in (nan, inf, -inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                StateFact("x", 1, NOW, "user", "src", confidence=value)
            with self.subTest(resource=value), self.assertRaises(ValueError):
                PlanStep("s", "act", "Act", resource_requirements={"cpu": value})

    def test_boolean_is_not_accepted_as_confidence_or_resource_quantity(self):
        with self.assertRaises(ValueError):
            StateFact("x", 1, NOW, "user", "src", confidence=True)
        with self.assertRaises(ValueError):
            PlanStep("s", "act", "Act", resource_requirements={"cpu": True})

    def test_validity_window_must_be_ordered(self):
        with self.assertRaisesRegex(ValueError, "valid_from"):
            StateFact(
                "x", 1, NOW, "user", "src",
                valid_from="2026-01-03T00:00:00Z",
                valid_until="2026-01-02T00:00:00Z",
            )

    def test_nested_state_values_are_defensively_frozen(self):
        source = {"nested": {"items": [1, 2]}}
        fact = StateFact("payload", source, NOW, "user", "src")
        source["nested"]["items"].append(3)
        self.assertEqual(fact.value["nested"]["items"], (1, 2))
        with self.assertRaises(TypeError):
            fact.value["new"] = "mutation"

    def test_plan_mappings_are_frozen(self):
        effects = {"status": {"flags": ["a"]}}
        step = PlanStep("s", "act", "Act", effects=effects)
        effects["status"]["flags"].append("b")
        self.assertEqual(step.effects["status"]["flags"], ("a",))
        with self.assertRaises(TypeError):
            step.effects["other"] = True

    def test_non_json_values_are_rejected(self):
        with self.assertRaises(ValueError):
            StateFact("x", object(), NOW, "user", "src")


class PlanValidationTests(unittest.TestCase):
    def make_plan(self, steps, domain="generic"):
        return Plan(
            plan_id="p1", goal_id="goal-1", domain=domain,
            state_revision=1, steps=tuple(steps), created_at=NOW,
        )

    def test_valid_dag_returns_deterministic_topological_order(self):
        plan = self.make_plan([
            PlanStep("finish", "finish", "Finish", depends_on=("prepare",)),
            PlanStep("prepare", "prepare", "Prepare"),
            PlanStep("inspect", "inspect", "Inspect", depends_on=("prepare",)),
        ])
        result = validate_plan(plan)
        self.assertTrue(result.valid)
        self.assertEqual(result.topological_order, ("prepare", "finish", "inspect"))

    def test_unknown_dependency_is_rejected(self):
        result = validate_plan(self.make_plan([
            PlanStep("s1", "act", "Act", depends_on=("missing",)),
        ]))
        self.assertFalse(result.valid)
        self.assertIn("unknown_dependency", {item.code for item in result.issues})

    def test_dependency_cycle_is_rejected(self):
        result = validate_plan(self.make_plan([
            PlanStep("a", "a", "A", depends_on=("b",)),
            PlanStep("b", "b", "B", depends_on=("a",)),
        ]))
        self.assertFalse(result.valid)
        self.assertIn("dependency_cycle", {item.code for item in result.issues})

    def test_duplicate_step_ids_are_rejected(self):
        result = validate_plan(self.make_plan([
            PlanStep("same", "a", "A"), PlanStep("same", "b", "B"),
        ]))
        self.assertFalse(result.valid)
        self.assertIn("duplicate_step_id", {item.code for item in result.issues})

    def test_high_risk_requires_human_approval(self):
        result = validate_plan(self.make_plan([
            PlanStep("s1", "act", "Act", risk=StepRisk.HIGH),
        ]))
        self.assertFalse(result.valid)
        self.assertIn("human_approval_required", {item.code for item in result.issues})

    def test_healthcare_policy_requires_evidence_and_approval(self):
        result = validate_plan(self.make_plan([
            PlanStep("s1", "clinical_action", "Clinical action", risk=StepRisk.CRITICAL),
        ], domain="healthcare"), domain_policy=HealthcareDomainAdapter().get_policy())
        codes = {item.code for item in result.issues}
        self.assertIn("human_approval_required", codes)
        self.assertIn("domain_evidence_required", codes)

    def test_healthcare_policy_passes_with_evidence_and_human_gate(self):
        result = validate_plan(self.make_plan([
            PlanStep("s1", "clinical_review", "Clinician review", risk=StepRisk.HIGH,
                     requires_human_approval=True, evidence_refs=("guideline:example:v1",)),
        ], domain="healthcare"), domain_policy=HealthcareDomainAdapter().get_policy())
        self.assertTrue(result.valid)

    def test_core_does_not_infer_healthcare_policy_from_domain_name(self):
        result = validate_plan(self.make_plan([
            PlanStep("s1", "clinical_action", "Clinical action", risk=StepRisk.HIGH,
                     requires_human_approval=True),
        ], domain="Healthcare"))
        self.assertTrue(result.valid)
        self.assertNotIn("domain_evidence_required", {item.code for item in result.issues})

    def test_domain_policy_mismatch_is_rejected(self):
        result = validate_plan(self.make_plan([PlanStep("s1", "act", "Act")], domain="healthcare"),
                               domain_policy=RoboticsDomainAdapter().get_policy())
        self.assertFalse(result.valid)
        self.assertIn("domain_policy_mismatch", {item.code for item in result.issues})

    def test_robotics_adapter_uses_same_universal_core(self):
        result = validate_plan(self.make_plan([
            PlanStep("s1", "move", "Move", risk=StepRisk.HIGH, requires_human_approval=True),
        ], domain="robotics"), domain_policy=RoboticsDomainAdapter().get_policy())
        self.assertTrue(result.valid)

    def test_max_steps_policy_is_enforced(self):
        result = validate_plan(
            self.make_plan([PlanStep("a", "a", "A"), PlanStep("b", "b", "B")]),
            PlanningPolicy(max_steps=1),
        )
        self.assertFalse(result.valid)
        self.assertIn("max_steps_exceeded", {item.code for item in result.issues})

    def test_mark_validated_returns_copy_and_does_not_execute(self):
        original = self.make_plan([PlanStep("s1", "observe", "Observe")])
        validated = mark_validated(original)
        self.assertNotEqual(original.status, validated.status)
        self.assertEqual(validated.status.value, "validated")
        self.assertEqual(original.status.value, "draft")

    def test_mark_validated_rejects_invalid_plan(self):
        original = self.make_plan([
            PlanStep("s1", "act", "Act", risk=StepRisk.CRITICAL),
        ])
        with self.assertRaises(ValueError):
            mark_validated(original)


if __name__ == "__main__":
    unittest.main()
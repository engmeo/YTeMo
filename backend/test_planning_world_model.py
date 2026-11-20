import unittest

from planning.models import StateSnapshot
from planning.world_model import (
    RuleBasedWorldModel,
    TransitionRule,
    WorldState,
)


def make_state(values=None, revision=4):
    snapshot = StateSnapshot(
        subject_id="subject-1",
        domain="general",
        revision=revision,
        as_of="2026-11-20T00:00:00Z",
        facts=(),
        constraints=(),
        unknowns=(),
    )
    return WorldState.from_snapshot(
        snapshot,
        values=values or {"status": "idle", "counter": 1},
    )


class WorldModelTests(unittest.TestCase):
    def test_predicts_transition_without_executing_action(self):
        state = make_state()
        model = RuleBasedWorldModel([
            TransitionRule(
                rule_id="rule-1",
                action="start",
                preconditions={"status": "idle"},
                effects={"status": "running"},
                uncertainty=0.1,
            )
        ])

        result = model.predict(state, "start")

        self.assertTrue(result.applicable)
        self.assertEqual(result.predicted_state.values["status"], "running")
        self.assertEqual(state.values["status"], "idle")
        self.assertEqual(result.predicted_state.revision, 5)
        self.assertAlmostEqual(result.confidence, 0.9)

    def test_unknown_precondition_blocks_prediction(self):
        state = make_state({"status": "idle"})
        model = RuleBasedWorldModel([
            TransitionRule(
                rule_id="rule-unknown",
                action="start",
                preconditions={"permission": True},
                effects={"status": "running"},
            )
        ])

        result = model.predict(state, "start")

        self.assertFalse(result.applicable)
        self.assertIsNone(result.predicted_state)
        self.assertEqual(result.confidence, 0.0)

    def test_mismatched_precondition_blocks_prediction(self):
        state = make_state({"status": "stopped"})
        model = RuleBasedWorldModel([
            TransitionRule(
                rule_id="rule-mismatch",
                action="start",
                preconditions={"status": "idle"},
                effects={"status": "running"},
            )
        ])

        result = model.predict(state, "start")
        self.assertFalse(result.applicable)
        self.assertIn("precondition mismatch: status", result.reasons)

    def test_evaluates_prediction_against_observation(self):
        state = make_state()
        model = RuleBasedWorldModel([
            TransitionRule(
                rule_id="rule-eval",
                action="increment",
                preconditions={"counter": 1},
                effects={"counter": 2},
            )
        ])
        prediction = model.predict(state, "increment")

        observed = make_state({"status": "idle", "counter": 2}, revision=5)
        evaluation = model.evaluate(prediction, observed)

        self.assertEqual(evaluation.accuracy, 1.0)
        self.assertEqual(evaluation.matched_keys, ("counter",))

    def test_rejects_duplicate_actions(self):
        rule = TransitionRule(
            rule_id="one",
            action="start",
            preconditions={},
            effects={},
        )
        with self.assertRaises(ValueError):
            RuleBasedWorldModel([rule, rule])

    def test_world_state_is_immutable(self):
        state = make_state()
        with self.assertRaises(TypeError):
            state.values["status"] = "changed"


if __name__ == "__main__":
    unittest.main()

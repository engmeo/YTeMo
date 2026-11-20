import unittest

from planning.world_model import (
    RuleBasedWorldModel,
    TransitionRule,
)

class WorldModelVersionTests(unittest.TestCase):
    def test_rule_replacement_requires_higher_version(self):
        model = RuleBasedWorldModel([
            TransitionRule("rule", "start", {}, {"status": "running"})
        ])
        with self.assertRaises(ValueError):
            model.register_rule(
                TransitionRule("rule", "start", {}, {"status": "active"})
            )

    def test_higher_rule_version_can_replace_existing_rule(self):
        model = RuleBasedWorldModel([
            TransitionRule("rule", "start", {}, {"status": "running"}, version=1)
        ])
        model.register_rule(
            TransitionRule("rule", "start", {}, {"status": "active"}, version=2)
        )
        self.assertEqual(model._rules["start"].version, 2)

    def test_prediction_records_rule_version(self):
        from planning.world_model import WorldState
        state = WorldState(
            subject_id="s", domain="general", revision=3,
            as_of="2026-11-20T00:00:00Z", values={}
        )
        model = RuleBasedWorldModel([
            TransitionRule("rule", "start", {}, {"status": "running"}, version=3)
        ])
        prediction = model.predict(state, "start")
        self.assertEqual(prediction.rule_version, 3)

    def test_stale_observation_is_rejected(self):
        from planning.world_model import WorldState
        state = WorldState(
            subject_id="s", domain="general", revision=3,
            as_of="2026-11-20T00:00:00Z", values={"status": "idle"}
        )
        model = RuleBasedWorldModel([
            TransitionRule("rule", "start", {}, {"status": "running"})
        ])
        prediction = model.predict(state, "start")
        stale = WorldState(
            subject_id="s", domain="general", revision=3,
            as_of="2026-11-20T00:00:00Z", values={"status": "running"}
        )
        with self.assertRaises(ValueError):
            model.evaluate(prediction, stale)


if __name__ == "__main__":
    unittest.main()

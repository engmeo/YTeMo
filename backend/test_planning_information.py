import unittest
from datetime import datetime, timezone
from math import isclose

from planning.models import BeliefHypothesis, BeliefState, StateSnapshot
from planning.belief_engine import EvidenceLikelihood, update_belief
from planning.information import detect_information_gaps
from planning.information_planner import build_information_steps
from planning.voi import evaluate_value_of_information

NOW = datetime.now(timezone.utc).isoformat()


def belief():
    snapshot = StateSnapshot("subject", "generic", 1, NOW,
        unknowns=("current battery level", "weather condition"))
    return BeliefState(snapshot, hypotheses=(
        BeliefHypothesis("h1", "Hypothesis one", 0.6),
        BeliefHypothesis("h2", "Hypothesis two", 0.4),
    ), unresolved_questions=("weather condition", "preferred route"))


class BeliefUpdateTests(unittest.TestCase):
    def test_bayesian_update_normalizes_posterior(self):
        result = update_belief(belief(), EvidenceLikelihood(
            "ev-1", "sensor", "sensor-1", NOW, {"h1": 0.8, "h2": 0.2}))
        probs = [h.probability for h in result.belief.hypotheses]
        self.assertTrue(isclose(sum(probs), 1.0))
        self.assertTrue(isclose(probs[0], 0.8571428571428571))
        self.assertGreater(result.entropy_reduction_bits, 0)
        self.assertIn("ev-1", result.belief.hypotheses[0].evidence_refs)

    def test_reliability_zero_leaves_prior_unchanged(self):
        result = update_belief(belief(), EvidenceLikelihood(
            "ev-neutral", "sensor", "sensor-1", NOW, {"h1": 0.01, "h2": 0.99}, reliability=0))
        self.assertTrue(isclose(result.belief.hypotheses[0].probability, 0.6))

    def test_duplicate_evidence_is_rejected(self):
        first = update_belief(belief(), EvidenceLikelihood("ev", "sensor", "s", NOW, {"h1": 0.8}))
        with self.assertRaisesRegex(ValueError, "already been applied"):
            update_belief(first.belief, EvidenceLikelihood("ev", "sensor", "s", NOW, {"h1": 0.8}))

    def test_unknown_hypothesis_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown hypotheses"):
            update_belief(belief(), EvidenceLikelihood("ev", "sensor", "s", NOW, {"other": 0.5}))

    def test_zero_probability_for_all_hypotheses_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "every hypothesis impossible"):
            update_belief(belief(), EvidenceLikelihood("ev", "sensor", "s", NOW, {"h1": 0, "h2": 0}))

    def test_evidence_requires_timezone_and_valid_likelihood(self):
        with self.assertRaises(ValueError):
            EvidenceLikelihood("ev", "sensor", "s", "2026-01-01T10:00:00", {"h1": 0.5})
        with self.assertRaises(ValueError):
            EvidenceLikelihood("ev", "sensor", "s", NOW, {"h1": 1.2})


class InformationPlanningTests(unittest.TestCase):
    def test_gap_detection_deduplicates_unknowns_and_questions(self):
        gaps = detect_information_gaps(belief())
        self.assertEqual([x.question for x in gaps], ["current battery level", "weather condition", "preferred route"])

    def test_gap_to_step_conversion_is_proposal_only(self):
        steps = build_information_steps(detect_information_gaps(belief()))
        self.assertEqual(len(steps), 3)
        self.assertTrue(all(x.action == "collect_information" for x in steps))
        self.assertTrue(all(x.metadata["proposal_only"] for x in steps))
        self.assertTrue(all(x.metadata["requires_authorized_collection"] for x in steps))

    def test_duplicate_gap_ids_are_rejected(self):
        gaps = detect_information_gaps(belief())
        with self.assertRaisesRegex(ValueError, "Duplicate information gap"):
            build_information_steps((gaps[0], gaps[0]))


class ValueOfInformationTests(unittest.TestCase):
    def test_positive_value_when_observation_changes_decision(self):
        result = evaluate_value_of_information(
            {"healthy": 0.5, "fault": 0.5},
            {"continue": {"healthy": 10, "fault": -10},
             "inspect": {"healthy": 2, "fault": 2}},
            {"positive": {"healthy": 0.1, "fault": 0.9},
             "negative": {"healthy": 0.9, "fault": 0.1}},
            information_cost=0.5,
        )
        self.assertEqual(result.current_best_decision, "inspect")
        self.assertGreater(result.gross_value, 0)
        self.assertGreater(result.net_value, 0)

    def test_information_cost_can_make_observation_not_worthwhile(self):
        result = evaluate_value_of_information(
            {"h1": 0.5, "h2": 0.5},
            {"d1": {"h1": 1, "h2": 0}, "d2": {"h1": 0, "h2": 1}},
            {"o1": {"h1": 0.9, "h2": 0.1}, "o2": {"h1": 0.1, "h2": 0.9}},
            information_cost=10,
        )
        self.assertLess(result.net_value, 0)

    def test_invalid_observation_distribution_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must sum to 1"):
            evaluate_value_of_information(
                {"h": 1}, {"d": {"h": 1}}, {"yes": {"h": 0.2}})

    def test_decisions_must_cover_every_hypothesis(self):
        with self.assertRaisesRegex(ValueError, "every hypothesis"):
            evaluate_value_of_information(
                {"h1": 0.5, "h2": 0.5}, {"d": {"h1": 1}},
                {"o1": {"h1": 1, "h2": 1}})


if __name__ == "__main__":
    unittest.main()

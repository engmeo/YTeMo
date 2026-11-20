import math
import unittest

from planning.causal import CausalEdge, CausalModel
from planning.counterfactual import evaluate_intervention
from planning.risk import RiskItem, assess_risks
from planning.robustness import Scenario, evaluate_robustness


class TestCausalPlanning(unittest.TestCase):
    def test_dag_order_and_intervention_propagation(self):
        model = CausalModel(
            nodes=("input", "middle", "outcome"),
            edges=(
                CausalEdge("input", "middle", 2.0),
                CausalEdge("middle", "outcome", 0.5),
            ),
            baseline_values={"input": 1, "middle": 10, "outcome": 20},
        )
        result = evaluate_intervention(model, {"input": 3})
        self.assertAlmostEqual(result.counterfactual["middle"], 14)
        self.assertAlmostEqual(result.counterfactual["outcome"], 22)
        self.assertAlmostEqual(result.deltas["outcome"], 2)

    def test_rejects_cycle(self):
        with self.assertRaises(ValueError):
            CausalModel(
                nodes=("a", "b"),
                edges=(CausalEdge("a", "b", 1), CausalEdge("b", "a", 1)),
                baseline_values={"a": 0, "b": 0},
            )

    def test_rejects_unknown_intervention(self):
        model = CausalModel(("a",), (), {"a": 0})
        with self.assertRaises(ValueError):
            evaluate_intervention(model, {"missing": 1})


class TestRiskPlanning(unittest.TestCase):
    def test_expected_loss_and_threshold(self):
        result = assess_risks(
            [RiskItem("r1", 0.5, 0.4), RiskItem("r2", 0.2, 0.5)],
            max_expected_loss=0.25,
        )
        self.assertAlmostEqual(result.total_expected_loss, 0.3)
        self.assertFalse(result.within_threshold)

    def test_rejects_out_of_range_probability(self):
        with self.assertRaises(ValueError):
            RiskItem("bad", 1.2, 0.5)


class TestRobustnessPlanning(unittest.TestCase):
    def test_expected_and_worst_case_scores(self):
        result = evaluate_robustness((
            Scenario("normal", 0.75, {"A": 10, "B": 8}),
            Scenario("stress", 0.25, {"A": 0, "B": 7}),
        ))
        by_id = {item.candidate_id: item for item in result}
        self.assertAlmostEqual(by_id["A"].expected_utility, 7.5)
        self.assertAlmostEqual(by_id["B"].expected_utility, 7.75)
        self.assertEqual(by_id["A"].worst_case_utility, 0)
        self.assertEqual(by_id["B"].worst_case_utility, 7)

    def test_rejects_mismatched_candidate_sets(self):
        with self.assertRaises(ValueError):
            evaluate_robustness((
                Scenario("s1", 1, {"A": 1}),
                Scenario("s2", 1, {"B": 1}),
            ))


if __name__ == "__main__":
    unittest.main()

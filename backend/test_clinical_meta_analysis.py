import unittest

from clinical_meta_analysis import pool_effects


class MetaAnalysisTests(unittest.TestCase):
    def test_random_effects_returns_heterogeneity(self):
        result = pool_effects([
            {"study_id": "s1", "effect_measure": "mean_difference", "effect": 1.2, "standard_error": 0.2},
            {"study_id": "s2", "effect_measure": "mean_difference", "effect": 1.4, "standard_error": 0.3},
        ])
        self.assertEqual(result["study_count"], 2)
        self.assertGreaterEqual(result["heterogeneity"]["i_squared_percent"], 0)
        self.assertLess(result["confidence_interval_95"][0], result["pooled_effect"])

    def test_rejects_mixed_effect_measures(self):
        with self.assertRaises(ValueError):
            pool_effects([
                {"study_id": "s1", "effect_measure": "OR", "effect": 0.2, "standard_error": 0.1},
                {"study_id": "s2", "effect_measure": "RR", "effect": 0.3, "standard_error": 0.1},
            ])

    def test_rejects_duplicate_studies(self):
        row = {"study_id": "same", "effect_measure": "MD", "effect": 1, "standard_error": 0.1}
        with self.assertRaises(ValueError):
            pool_effects([row, row])


if __name__ == "__main__":
    unittest.main()

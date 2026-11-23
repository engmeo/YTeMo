import unittest
from decimal import Decimal
from healthcare_cost_intelligence import (
    CostIntelligenceError, normalize_cost_items, analyze_patient_journey_cost,
    estimate_bhyt_payment, build_cost_intelligence_report
)


class CostIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            {"item_id":"v1","category":"visit","description":"Kham","quantity":1,"unit_price":150000,"currency":"VND"},
            {"item_id":"m1","category":"medicine","description":"Thuoc A","quantity":2,"unit_price":25000,"currency":"VND"},
            {"item_id":"l1","category":"lab","description":"Glucose","quantity":1,"unit_price":50000,"currency":"VND"},
        ]

    def test_line_math_and_category_totals(self):
        result = analyze_patient_journey_cost(self.items)
        self.assertEqual(result["total"], "250000.00")
        self.assertEqual(result["by_category"]["medicine"], "50000.00")
        self.assertEqual(result["line_count"], 3)

    def test_bhyt_explicit_rate_arithmetic(self):
        result = estimate_bhyt_payment(eligible_amount=200000, coverage_rate=80, patient_cap=150000)
        self.assertEqual(result["estimated_insurer_payment"], "150000.00")
        self.assertEqual(result["estimated_patient_share_of_eligible_amount"], "50000.00")
        self.assertTrue(result["requires_human_verification"])

    def test_rejects_mixed_currency(self):
        rows = self.items + [{"category":"other","description":"USD","quantity":1,"unit_price":2,"currency":"USD"}]
        with self.assertRaises(CostIntelligenceError):
            analyze_patient_journey_cost(rows)

    def test_rejects_invalid_rate_and_negative_values(self):
        with self.assertRaises(CostIntelligenceError):
            estimate_bhyt_payment(eligible_amount=100, coverage_rate=101)
        with self.assertRaises(CostIntelligenceError):
            normalize_cost_items([{"category":"lab","description":"x","quantity":-1,"unit_price":5}])

    def test_rejects_duplicate_ids_and_unknown_category(self):
        with self.assertRaises(CostIntelligenceError):
            normalize_cost_items([
                {"item_id":"x","category":"lab","description":"a","unit_price":1},
                {"item_id":"x","category":"lab","description":"b","unit_price":1}
            ])
        with self.assertRaises(CostIntelligenceError):
            normalize_cost_items([{"category":"diagnosis","description":"x","unit_price":1}])

    def test_report_keeps_clinical_boundaries(self):
        result = build_cost_intelligence_report(
            cost_items=self.items,
            bhyt={"eligible_amount":100000,"coverage_rate":80},
            medication_items=[self.items[1]],
            lab_items=[self.items[2]]
        )
        self.assertEqual(result["bhyt"]["status"], "estimate_only")
        self.assertIn("Khong tu de xuat", result["medication_costs"]["safety_note"])
        self.assertIn("khong phai cong cu", result["clinical_boundary"])

    def test_empty_input_is_not_fabricated(self):
        result = analyze_patient_journey_cost([])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["total"], "0.00")


if __name__ == "__main__":
    unittest.main(verbosity=2)

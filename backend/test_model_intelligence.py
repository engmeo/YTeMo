import unittest

from model_intelligence import choose_profile, model_catalog


class ModelIntelligenceTests(unittest.TestCase):
    def test_routine_message_uses_fast_profile(self):
        self.assertEqual(choose_profile("Tôi nên uống bao nhiêu nước mỗi ngày?"), "fast")

    def test_complex_context_escalates_reasoning(self):
        self.assertEqual(choose_profile("Tôi đang dùng nhiều thuốc và có bệnh nền"), "reasoning")

    def test_clinical_medication_question_uses_medical_profile(self):
        self.assertEqual(choose_profile("Tôi muốn hỏi về một loại thuốc"), "medical")

    def test_explicit_profile_is_respected(self):
        self.assertEqual(choose_profile("Xin chào", requested_profile="reasoning"), "reasoning")

    def test_catalog_marks_models_as_not_default_enabled(self):
        catalog = model_catalog()
        self.assertGreaterEqual(len(catalog["models"]), 4)
        self.assertTrue(all(item["default_enabled"] is False for item in catalog["models"]))


if __name__ == "__main__":
    unittest.main()

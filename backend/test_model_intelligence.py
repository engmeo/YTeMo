import unittest
from unittest.mock import Mock, patch

import model_intelligence
from model_intelligence import choose_profile, model_catalog, route_request


class ModelIntelligenceTests(unittest.TestCase):
    def test_routine_message_uses_fast_profile(self):
        self.assertEqual(choose_profile("Tôi nên uống bao nhiêu nước mỗi ngày?"), "fast")

    def test_complex_context_escalates_reasoning(self):
        self.assertEqual(choose_profile("Tôi đang dùng nhiều thuốc và có bệnh nền"), "reasoning")

    def test_clinical_medication_question_uses_medical_profile(self):
        self.assertEqual(choose_profile("Tôi muốn hỏi về một loại thuốc"), "medical")

    def test_explicit_profile_is_respected(self):
        self.assertEqual(choose_profile("Xin chào", requested_profile="reasoning"), "reasoning")

    def test_router_detects_vietnamese_medical_intent_with_or_without_diacritics(self):
        self.assertEqual(choose_profile("Tôi muốn hỏi về thuốc"), "medical")
        self.assertEqual(choose_profile("toi muon hoi ve thuoc"), "medical")

    def test_router_escalates_multi_domain_requests_to_reasoning(self):
        route = route_request("Tổng hợp kết quả xét nghiệm và chi phí điều trị")
        self.assertEqual(route["profile"], "reasoning")
        self.assertIn("laboratory", route["intents"])
        self.assertIn("cost", route["intents"])

    def test_emergency_signals_use_fast_profile_and_are_flagged(self):
        route = route_request("Tôi đang khó thở")
        self.assertEqual(route["profile"], "fast")
        self.assertTrue(route["emergency_signal"])

    def test_catalog_marks_models_as_not_default_enabled(self):
        catalog = model_catalog()
        self.assertGreaterEqual(len(catalog["models"]), 4)
        self.assertTrue(all(item["default_enabled"] is False for item in catalog["models"]))

    @patch("model_intelligence.requests.post")
    def test_stream_yields_text_deltas_without_buffering(self, post):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.raise_for_status = Mock()
        response.iter_lines.return_value = [
            b'data: {"choices":[{"delta":{"content":"Xin "}}]}',
            b'data: {"choices":[{"delta":{"content":"chao"}}]}',
            b'data: [DONE]',
        ]
        post.return_value = response

        with patch.dict("os.environ", {
            "YTEMO_MODEL_BACKEND": "openrouter",
            "OPENROUTER_API_KEY": "test-key",
            "YTEMO_FAST_MODEL": "test-model",
        }):
            chunks = list(model_intelligence.generate_stream(
                [{"role": "user", "content": "hello"}],
                profile="fast",
            ))

        self.assertEqual(chunks, ["Xin ", "chao"])
        self.assertTrue(post.call_args.kwargs["stream"])
        self.assertTrue(post.call_args.kwargs["json"]["stream"])

    @patch("model_intelligence.requests.post")
    def test_stream_converts_provider_timeout_to_gateway_error(self, post):
        import requests
        post.side_effect = requests.Timeout("provider timeout")
        with patch.dict("os.environ", {
            "YTEMO_MODEL_BACKEND": "openrouter",
            "OPENROUTER_API_KEY": "test-key",
        }):
            with self.assertRaises(model_intelligence.ModelGatewayError):
                list(model_intelligence.generate_stream(
                    [{"role": "user", "content": "hello"}],
                    profile="fast",
                ))


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

import multi_agent_orchestrator as orchestration


def fake_generate(messages, profile="fast", max_tokens=500, temperature=0.1):
    prompt = messages[-1]["content"]
    if "Bạn là Supervisor của hệ thống Y TẾ MỞ" in prompt:
        return {"text": '{"agents":["laboratory","cost"],"reason":"Cần đối chiếu hai miền."}', "latency_ms": 10}
    if "ĐỊNH DẠNG BÁO CÁO" in prompt:
        role = messages[0]["content"]
        return {"text": f"Findings: dữ kiện từ nguồn. Evidence: trích dẫn được cung cấp. Role: {role}", "latency_ms": 15}
    if "Bạn là Supervisor tổng hợp" in prompt:
        return {"text": "Bản tổng hợp: Tôi đã đối chiếu thông tin xét nghiệm và chi phí được cung cấp.", "latency_ms": 20}
    if "Reviewer độc lập" in prompt:
        return {"text": "APPROVE", "latency_ms": 5}
    raise AssertionError("Unexpected LLM stage: " + prompt[:120])


class MultiAgentOrchestrationTests(unittest.TestCase):
    @patch("multi_agent_orchestrator.generate", side_effect=fake_generate)
    def test_supervisor_fans_out_to_parallel_domain_specialists_then_synthesizes_and_reviews(self, generate):
        result = orchestration.run_multi_agent(
            "Tổng hợp kết quả xét nghiệm và chi phí điều trị"
        )
        self.assertEqual(result["review"], "APPROVE")
        self.assertIn("Bản tổng hợp", result["reply"])
        self.assertIn("laboratory", result["selected_agents"])
        self.assertIn("cost", result["selected_agents"])
        completed = {item["agent"] for item in result["agent_results"] if item["status"] == "completed"}
        self.assertTrue({"laboratory", "cost"}.issubset(completed))
        # planner + two specialists + synthesis + independent reviewer
        self.assertEqual(generate.call_count, 5)

    @patch("multi_agent_orchestrator.generate", side_effect=fake_generate)
    def test_reviewer_rejection_prevents_unverified_draft_from_reaching_user(self, generate):
        def reject(messages, profile="fast", max_tokens=500, temperature=0.1):
            if "Reviewer độc lập" in messages[-1]["content"]:
                return {"text": "REJECT"}
            return fake_generate(messages, profile, max_tokens, temperature)

        generate.side_effect = reject
        result = orchestration.run_multi_agent("Tôi muốn hỏi về thuốc")
        self.assertEqual(result["review"], "REJECT")
        self.assertNotIn("Bản tổng hợp", result["reply"])
        self.assertIn("chưa xác minh", result["reply"])

    def test_general_chat_does_not_pay_multi_agent_overhead(self):
        self.assertFalse(orchestration.is_multi_agent_request("Xin chào, hôm nay thế nào?"))

    @patch("multi_agent_orchestrator.generate", side_effect=fake_generate)
    def test_document_analysis_requires_explicit_specialist_selection_and_keeps_source_context(self, generate):
        result = orchestration.run_multi_agent(
            "Phân tích hồ sơ được cung cấp",
            document_context="Thuốc A 5 mg mỗi ngày. HbA1c 7.2%.",
            requested_agents=["medication", "laboratory"],
        )
        self.assertIn("medication", result["selected_agents"])
        self.assertIn("laboratory", result["selected_agents"])
        specialist_prompts = [
            call.args[0][-1]["content"]
            for call in generate.call_args_list
            if "ĐỊNH DẠNG BÁO CÁO" in call.args[0][-1]["content"]
        ]
        self.assertTrue(all("Thuốc A 5 mg" in prompt for prompt in specialist_prompts))


if __name__ == "__main__":
    unittest.main()

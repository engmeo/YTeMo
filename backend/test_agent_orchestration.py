import unittest
from unittest.mock import patch

import agent


class CompanionOrchestrationTests(unittest.TestCase):
    def test_emergency_message_uses_deterministic_fast_path(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("agent.generate_stream", side_effect=AssertionError("LLM must not run")):
                reply = agent.chat("Tôi đang khó thở")
                streamed = "".join(agent.chat_stream("Tôi đang khó thở"))
        self.assertIn("115", reply)
        self.assertIn("115", streamed)

    def test_non_emergency_message_is_not_forced_into_emergency_path(self):
        with patch.dict("os.environ", {}, clear=True):
            with patch("agent.generate_content") as generate:
                generate.return_value.text = "Tôi có thể hỗ trợ bạn."
                reply = agent.chat("Tôi không bị khó thở, chỉ muốn hỏi về lịch khám.")
        self.assertEqual(reply, "Tôi có thể hỗ trợ bạn.")
        generate.assert_called_once()


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch, Mock

import gemini_service
from gemini_service import (
    generate_content,
    get_gemini_client,
    GeminiServiceError,
)


class FakeResponse:
    text = "OK"


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)


class TemporaryError(Exception):
    code = 504


class PermanentError(Exception):
    code = 400


class GeminiServiceTests(unittest.TestCase):
    def test_success_without_retry(self):
        client = FakeClient([FakeResponse()])
        result = generate_content("test-model", "hello", client=client)
        self.assertEqual(result.text, "OK")
        self.assertEqual(client.models.calls, 1)

    @patch("gemini_service.time.sleep")
    def test_retries_temporary_error_then_succeeds(self, sleep):
        client = FakeClient([TemporaryError("deadline"), FakeResponse()])
        result = generate_content("test-model", "hello", client=client)
        self.assertEqual(result.text, "OK")
        self.assertEqual(client.models.calls, 2)
        sleep.assert_called_once_with(2)

    @patch("gemini_service.time.sleep")
    def test_does_not_retry_permanent_error(self, sleep):
        client = FakeClient([PermanentError("bad request")])
        with self.assertRaises(GeminiServiceError):
            generate_content("test-model", "hello", client=client)
        self.assertEqual(client.models.calls, 1)
        sleep.assert_not_called()

    @patch("gemini_service.time.sleep")
    def test_stops_after_three_attempts(self, sleep):
        client = FakeClient([
            TemporaryError("temporary 1"),
            TemporaryError("temporary 2"),
            TemporaryError("temporary 3"),
        ])
        with self.assertRaises(GeminiServiceError):
            generate_content("test-model", "hello", client=client)
        self.assertEqual(client.models.calls, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4])

    @patch("gemini_service.genai.Client")
    def test_client_has_timeout_and_sdk_retry_disabled(self, client_constructor):
        previous = gemini_service._client
        gemini_service._client = None
        try:
            get_gemini_client(api_key="test-key")
            kwargs = client_constructor.call_args.kwargs
            options = kwargs["http_options"]
            self.assertEqual(options.timeout, 30000)
            self.assertEqual(options.retry_options.attempts, 1)
        finally:
            gemini_service._client = previous


if __name__ == "__main__":
    unittest.main()

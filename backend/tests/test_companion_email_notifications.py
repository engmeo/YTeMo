from types import SimpleNamespace
from urllib.error import HTTPError

import companion_email_notifications as notifications
from temporal_action_worker import RetryableActionError


class FakeAuthAdmin:
    def get_user_by_id(self, user_id):
        assert user_id == "owner-1"
        return SimpleNamespace(user=SimpleNamespace(
            email="owner@example.test",
            email_confirmed_at="2026-11-01T00:00:00Z",
        ))


class FakeDB:
    auth = SimpleNamespace(admin=FakeAuthAdmin())


class FakeResponse:
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return b'{"id":"email-123"}'


def reminder_arguments(**overrides):
    args = {
        "title": "Tái khám",
        "due_at": "2026-12-01T09:00:00+07:00",
        "delivery_channel": "email",
        "email_consent": True,
        "email_consent_recorded_at": "2026-11-24T10:00:00+00:00",
        "_action_task_id": "task-123",
    }
    args.update(overrides)
    return args


def test_reminder_email_requires_explicit_channel_consent_and_task_id(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "care@example.test")
    handler = notifications.make_reminder_email_handler(FakeDB())
    import pytest
    with pytest.raises(ValueError, match="consent"):
        handler("owner-1", reminder_arguments(email_consent=False))
    with pytest.raises(ValueError, match="task ID"):
        handler("owner-1", reminder_arguments(_action_task_id=""))


def test_reminder_email_uses_verified_owner_email_and_task_idempotency(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "care@example.test")
    captured = {}
    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = request.headers
        captured["payload"] = request.data.decode("utf-8")
        captured["timeout"] = timeout
        return FakeResponse()
    monkeypatch.setattr(notifications, "urlopen", fake_urlopen)
    handler = notifications.make_reminder_email_handler(FakeDB())
    result = handler("owner-1", reminder_arguments())
    assert result["message_id"] == "email-123"
    assert result["recipient"] == "owner@example.test"
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["timeout"] == 15
    assert captured["headers"]["Idempotency-key"] == "ytemo-reminder-task-123"
    assert '"to": ["owner@example.test"]' in captured["payload"]


def test_resend_server_errors_are_retryable(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "care@example.test")
    def fail_urlopen(request, timeout):
        raise HTTPError(request.full_url, 503, "unavailable", {}, None)
    monkeypatch.setattr(notifications, "urlopen", fail_urlopen)
    handler = notifications.make_reminder_email_handler(FakeDB())
    import pytest
    with pytest.raises(RetryableActionError):
        handler("owner-1", reminder_arguments())

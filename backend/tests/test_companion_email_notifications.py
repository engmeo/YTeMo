from types import SimpleNamespace

import companion_email_notifications as notifications


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


def test_reminder_email_requires_explicit_email_channel(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "care@example.test")
    handler = notifications.make_reminder_email_handler(FakeDB())
    import pytest
    with pytest.raises(ValueError):
        handler("owner-1", {"title": "Follow up", "due_at": "2026-12-01T09:00:00+07:00"})


def test_reminder_email_uses_verified_owner_email_and_idempotency(monkeypatch):
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
    result = handler("owner-1", {
        "title": "Tái khám", "due_at": "2026-12-01T09:00:00+07:00",
        "delivery_channel": "email",
    })
    assert result["message_id"] == "email-123"
    assert result["recipient"] == "owner@example.test"
    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["timeout"] == 15
    assert any(key.lower() == "idempotency-key" for key in captured["headers"])
    assert '"to": ["owner@example.test"]' in captured["payload"]

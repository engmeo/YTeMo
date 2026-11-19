from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

from companion_core import CompanionCore, ConsentScope


def make_core(state):
    core = object.__new__(CompanionCore)
    core._load = lambda _user: state
    return core


def make_state(scope, items, granted=True):
    return SimpleNamespace(
        consents={scope.value: SimpleNamespace(granted=granted)},
        context_items=items,
    )


def item(scope, expiry=None):
    return SimpleNamespace(scope=scope, expires_at=expiry)


def test_context_without_expiry_remains_available():
    scope = next(iter(ConsentScope))
    ctx = item(scope)
    state = make_state(scope, [ctx])
    assert make_core(state).get_context("test-user") == [ctx]


def test_expired_context_is_not_returned():
    scope = next(iter(ConsentScope))
    expiry = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    ctx = item(scope, expiry)
    state = make_state(scope, [ctx])
    assert make_core(state).get_context("test-user") == []


def test_invalid_expiry_is_rejected():
    scope = next(iter(ConsentScope))
    ctx = item(scope, "not-a-date")
    state = make_state(scope, [ctx])
    assert make_core(state).get_context("test-user") == []


def test_future_expiry_remains_available():
    scope = next(iter(ConsentScope))
    expiry = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    ctx = item(scope, expiry)
    state = make_state(scope, [ctx])
    assert make_core(state).get_context("test-user") == [ctx]


def test_revoking_consent_clears_only_its_scope():
    scopes = list(ConsentScope)
    if len(scopes) < 2:
        return
    revoked, retained = scopes[0], scopes[1]
    old = item(revoked)
    other = item(retained)
    state = make_state(revoked, [old, other])

    core = object.__new__(CompanionCore)
    core._load_or_create = lambda _user: state
    core._add_event = lambda *args: None
    core.snapshot = lambda _user: {}
    core.repository = SimpleNamespace(save=lambda _state: None)

    core.set_consent("test-user", revoked, False)

    assert old not in state.context_items
    assert other in state.context_items
    assert state.consents[revoked.value].granted is False

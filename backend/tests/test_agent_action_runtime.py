from datetime import datetime, timedelta, timezone

import pytest

from agent_action_runtime import (
    ActionValidationError, approve_action, propose_action, reject_action,
)


class Query:
    def __init__(self, table):
        self.table = table
        self.filters = {}
        self.payload = None
        self.limit_value = None

    def select(self, *_): return self
    def insert(self, payload):
        self.payload = payload
        return self
    def update(self, payload):
        self.payload = payload
        return self
    def eq(self, key, value):
        self.filters[key] = value
        return self
    def limit(self, value):
        self.limit_value = value
        return self
    def order(self, *_args, **_kwargs): return self
    def execute(self):
        if self.payload and "user_id" in self.payload and "action_type" in self.payload:
            row = {"id": "action-1", **self.payload}
            self.table.rows.append(row)
            return type("Result", (), {"data": [row]})()
        matches = [r for r in self.table.rows if all(r.get(k) == v for k, v in self.filters.items())]
        if self.payload and matches:
            for row in matches:
                row.update(self.payload)
            return type("Result", (), {"data": matches})()
        return type("Result", (), {"data": matches[:self.limit_value] if self.limit_value else matches})()


class Table:
    def __init__(self): self.rows = []
    def table(self, _): return self
    def select(self, *_): return Query(self)
    def insert(self, payload): return Query(self).insert(payload)
    def update(self, payload): return Query(self).update(payload)


class DB:
    def __init__(self): self.rows = []
    def table(self, _): return Query(self)


def test_proposal_requires_explicit_approval_and_is_idempotent():
    db = DB()
    due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    first = propose_action(db, "owner-a", "create_reminder", {"title": "Tái khám", "due_at": due, "delivery_channel": "email"})
    second = propose_action(db, "owner-a", "create_reminder", {"title": "Tái khám", "due_at": due, "delivery_channel": "email"})
    assert first["status"] == "awaiting_approval"
    assert second["id"] == first["id"]
    assert len(db.rows) == 1
    approved = approve_action(db, "owner-a", first["id"])
    assert approved["status"] == "queued"


def test_cannot_approve_another_users_action():
    db = DB()
    due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    action = propose_action(db, "owner-a", "create_reminder", {"title": "Tái khám", "due_at": due, "delivery_channel": "email"})
    with pytest.raises(LookupError):
        approve_action(db, "owner-b", action["id"])


def test_unknown_action_is_rejected():
    with pytest.raises(ActionValidationError):
        propose_action(DB(), "owner-a", "run_arbitrary_code", {})


def test_reminder_requires_timezone_aware_timestamp():
    with pytest.raises(ActionValidationError):
        propose_action(DB(), "owner-a", "create_reminder", {"title": "Tái khám", "due_at": "2026-12-01T09:00:00"})


def test_rejection_closes_pending_proposal():
    db = DB()
    due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    action = propose_action(db, "owner-a", "create_reminder", {"title": "Tái khám", "due_at": due, "delivery_channel": "email"})
    rejected = reject_action(db, "owner-a", action["id"])
    assert rejected["status"] == "rejected"

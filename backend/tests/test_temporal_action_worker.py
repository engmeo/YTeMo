from datetime import datetime, timedelta, timezone

import temporal_action_worker as worker


class FakeQuery:
    def __init__(self, db):
        self.db = db
        self.filters = {}
        self.payload = None
    def update(self, payload):
        self.payload = payload
        return self
    def eq(self, key, value):
        self.filters[key] = value
        return self
    def select(self, *_):
        return self
    def execute(self):
        matched = [row for row in self.db.rows if all(row.get(k) == v for k, v in self.filters.items())]
        if self.payload is not None:
            for row in matched:
                row.update(self.payload)
            return type("Result", (), {"data": [dict(row) for row in matched]})()
        return type("Result", (), {"data": [dict(row) for row in matched]})()


class FakeRPC:
    def __init__(self, tasks):
        self.tasks = tasks
    def execute(self):
        return type("Result", (), {"data": self.tasks})()


class FakeDB:
    def __init__(self, tasks):
        self.rows = [dict(task) for task in tasks]
        self.tasks = [dict(task) for task in tasks]
    def rpc(self, name, args):
        assert name == "claim_companion_action_tasks"
        assert args["p_limit"] <= 50
        return FakeRPC(self.tasks)
    def table(self, _):
        return FakeQuery(self)


def task(**overrides):
    value = {
        "id": "task-1", "user_id": "owner-1",
        "action_type": "create_reminder", "arguments": {"title": "Follow up"},
        "status": "running", "attempt_count": 1, "max_attempts": 5,
        "lease_expires_at": (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat(),
    }
    value.update(overrides)
    return value


def test_worker_completes_claimed_task_and_passes_stable_task_id(monkeypatch):
    monkeypatch.setattr(worker, "_HANDLERS", {})
    seen = {}
    worker.register_handler("create_reminder", lambda user_id, args: seen.update({"user": user_id, "args": args}) or {"sent": True})
    db = FakeDB([task()])
    result = worker.run_once(db)
    assert result["completed"] == 1
    assert seen["user"] == "owner-1"
    assert seen["args"]["_action_task_id"] == "task-1"
    assert db.rows[0]["status"] == "completed"
    assert db.rows[0]["lease_expires_at"] is None


def test_worker_requeues_transient_failure_with_backoff(monkeypatch):
    monkeypatch.setattr(worker, "_HANDLERS", {})
    def transient(_user_id, _args):
        raise worker.RetryableActionError("temporary")
    worker.register_handler("create_reminder", transient)
    db = FakeDB([task()])
    result = worker.run_once(db)
    assert result["retried"] == 1
    assert db.rows[0]["status"] == "queued"
    assert db.rows[0]["next_attempt_at"]
    assert db.rows[0]["lease_expires_at"] is None


def test_worker_marks_transient_failure_failed_after_retry_budget(monkeypatch):
    monkeypatch.setattr(worker, "_HANDLERS", {})
    worker.register_handler("create_reminder", lambda *_: (_ for _ in ()).throw(worker.RetryableActionError("temporary")))
    db = FakeDB([task(attempt_count=5, max_attempts=5)])
    result = worker.run_once(db)
    assert result["failed"] == 1
    assert db.rows[0]["status"] == "failed"


def test_worker_fails_closed_for_unregistered_handler(monkeypatch):
    monkeypatch.setattr(worker, "_HANDLERS", {})
    db = FakeDB([task(action_type="unregistered")])
    result = worker.run_once(db)
    assert result["failed"] == 1
    assert db.rows[0]["status"] == "failed"


def test_worker_does_not_overwrite_a_reclaimed_lease(monkeypatch):
    monkeypatch.setattr(worker, "_HANDLERS", {})
    db = FakeDB([task()])
    def slow_handler(_user_id, _args):
        db.rows[0]["lease_expires_at"] = "newer-worker-lease"
        return {"sent": True}
    worker.register_handler("create_reminder", slow_handler)
    result = worker.run_once(db)
    assert result["skipped"] == 1
    assert db.rows[0]["status"] == "running"

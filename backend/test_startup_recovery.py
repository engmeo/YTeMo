
import ast
import threading
import time
import unittest
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.limit_value = None

    def select(self, *args):
        return self

    def eq(self, key, value):
        self.filters.append(("eq", key, value))
        return self

    def lt(self, key, value):
        self.filters.append(("lt", key, value))
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def execute(self):
        result = list(self.rows)
        for kind, key, value in self.filters:
            if kind == "eq":
                result = [r for r in result if r.get(key) == value]
            elif kind == "lt":
                result = [r for r in result if r.get(key) < value]
        if self.limit_value is not None:
            result = result[:self.limit_value]
        return SimpleNamespace(data=result)


class FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def table(self, name):
        assert name == "agent_tasks"
        query = FakeQuery(self.rows)
        self.queries.append(query)
        return query


def load_recovery(db, worker):
    source_path = Path(__file__).resolve().with_name("main.py")
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    matches = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_recover_agent_tasks_on_startup"
    ]
    if len(matches) != 1:
        raise AssertionError("Khong tim thay duy nhat ham startup recovery")

    namespace = {
        "datetime": datetime,
        "timezone": timezone,
        "timedelta": timedelta,
        "ThreadPoolExecutor": ThreadPoolExecutor,
        "db_client": db,
        "_run_agent_task": worker,
        "print": lambda *args, **kwargs: None,
    }
    module = ast.Module(body=[matches[0]], type_ignores=[])
    exec(compile(module, "main.py", "exec"), namespace)
    return namespace["_recover_agent_tasks_on_startup"]


def make_task(task_id, status, age_minutes):
    updated = datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    return {
        "id": task_id,
        "user_id": "test-user",
        "status": status,
        "updated_at": updated.isoformat(),
        "created_at": updated.isoformat(),
    }


class StartupRecoveryTests(unittest.TestCase):

    def test_only_queued_and_expired_running_are_recovered(self):
        rows = [
            make_task("queued-1", "queued", 1),
            make_task("expired-1", "running", 30),
            make_task("fresh-1", "running", 2),
            make_task("completed-1", "completed", 60),
            make_task("failed-1", "failed", 60),
        ]
        db = FakeDB(rows)
        processed = []

        recovery = load_recovery(
            db,
            lambda user_id, task_id: processed.append(task_id)
        )
        recovery()

        self.assertCountEqual(
            processed,
            ["queued-1", "expired-1"]
        )
        self.assertEqual(len(db.queries), 2)

        statuses = [
            next(
                value for kind, key, value in query.filters
                if kind == "eq" and key == "status"
            )
            for query in db.queries
        ]
        self.assertCountEqual(statuses, ["queued", "running"])

        expired_query = next(
            q for q in db.queries
            if ("eq", "status", "running") in q.filters
        )
        self.assertTrue(
            any(kind == "lt" and key == "updated_at"
                for kind, key, value in expired_query.filters)
        )

    def test_recovery_never_runs_more_than_two_workers(self):
        rows = [
            make_task(f"queued-{i}", "queued", 1)
            for i in range(7)
        ]
        db = FakeDB(rows)
        lock = threading.Lock()
        active = 0
        maximum_active = 0
        processed = []

        def worker(user_id, task_id):
            nonlocal active, maximum_active
            with lock:
                active += 1
                maximum_active = max(maximum_active, active)
            time.sleep(0.05)
            with lock:
                processed.append(task_id)
                active -= 1

        recovery = load_recovery(db, worker)
        recovery()

        self.assertEqual(len(processed), 7)
        self.assertLessEqual(maximum_active, 2)
        self.assertGreaterEqual(maximum_active, 2)

    def test_one_task_error_does_not_stop_other_tasks(self):
        rows = [
            make_task(f"queued-{i}", "queued", 1)
            for i in range(4)
        ]
        db = FakeDB(rows)
        processed = []
        lock = threading.Lock()

        def worker(user_id, task_id):
            with lock:
                processed.append(task_id)
            if task_id == "queued-1":
                raise RuntimeError("simulated task error")

        recovery = load_recovery(db, worker)
        recovery()

        self.assertCountEqual(
            processed,
            ["queued-0", "queued-1", "queued-2", "queued-3"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

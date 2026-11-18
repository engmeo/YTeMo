import unittest
from agent_core import extract_missing_information, build_research_checklist, AgentCore, AgentCoreError

class AgentCoreToolsTests(unittest.TestCase):
    def test_extracts_missing_context(self):
        result = extract_missing_information({"goal": "Tôi muốn giảm chi phí khám"})
        self.assertGreaterEqual(len(result["missing_information"]), 1)
        self.assertIn("không phải kết luận y khoa", result["note"])

    def test_research_checklist_disclaims_unverified_data(self):
        result = build_research_checklist({"goal": "Tìm hiểu quyền lợi"})
        self.assertEqual(len(result["research_topics"]), 3)
        self.assertIn("chưa có dữ liệu bên ngoài", result["warning"])

    def test_plan_rejects_unknown_tool(self):
        class FakeResponse:
            text = '{"steps":[{"key":"x","title":"x","tool":"delete_patient","input":{}}]}'
        class FakeModels:
            def generate_content(self, **kwargs): return FakeResponse()
        class FakeGemini:
            models = FakeModels()
        class FakeDB: pass
        core = AgentCore(FakeDB(), gemini_client=FakeGemini())
        with self.assertRaises(AgentCoreError):
            core._make_plan("test")


class AtomicClaimTests(unittest.TestCase):
    def test_two_workers_only_one_can_claim_task(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor

        class Response:
            def __init__(self, data):
                self.data = data

        class FakeDB:
            def __init__(self):
                self.task = {
                    "id": "task-1",
                    "user_id": "user-1",
                    "goal": "test",
                    "status": "queued",
                    "plan": [],
                    "error": None,
                }
                self.lock = threading.Lock()

            def table(self, name):
                return FakeQuery(self, name)

        class FakeQuery:
            def __init__(self, db, table):
                self.db = db
                self.table_name = table
                self.operation = None
                self.values = {}
                self.filters = []
                self.status_filter = None
                self.lt_filters = []

            def update(self, values):
                self.operation = "update"
                self.values = values
                return self

            def select(self, *columns):
                if self.operation is None:
                    self.operation = "select"
                return self

            def eq(self, column, value):
                self.filters.append((column, value))
                return self

            def in_(self, column, values):
                self.status_filter = (column, list(values))
                return self

            def lt(self, column, value):
                self.lt_filters.append((column, value))
                return self

            def limit(self, value):
                return self

            def execute(self):
                with self.db.lock:
                    row = self.db.task

                    if self.table_name != "agent_tasks":
                        return Response([])

                    for column, value in self.filters:
                        if row.get(column) != value:
                            return Response([])

                    if self.operation == "select":
                        return Response([dict(row)])

                    if self.operation == "update":
                        if self.status_filter:
                            column, allowed = self.status_filter
                            if row.get(column) not in allowed:
                                return Response([])

                        for column, cutoff in self.lt_filters:
                            value = row.get(column)
                            if value is None or value >= cutoff:
                                return Response([])

                        row.update(self.values)
                        return Response([dict(row)])

                    return Response([])

        db = FakeDB()
        core = AgentCore(db, gemini_client=object())
        barrier = threading.Barrier(2)

        def worker_claim():
            barrier.wait()
            return core._claim_task("task-1", "user-1")

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker_claim) for _ in range(2)]
            results = [future.result(timeout=5) for future in futures]

        successes = [item for item in results if item is not None]
        failures = [item for item in results if item is None]

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual(db.task["status"], "running")

    def test_running_task_is_not_claimed_again(self):
        class Response:
            def __init__(self, data):
                self.data = data

        class FakeDB:
            def __init__(self):
                self.task = {
                    "id": "task-2",
                    "user_id": "user-1",
                    "goal": "test",
                    "status": "running",
                    "plan": [],
                    "error": None,
                }

            def table(self, name):
                return FakeQuery(self, name)

        class FakeQuery:
            def __init__(self, db, table):
                self.db = db
                self.operation = None
                self.values = {}
                self.filters = []
                self.status_filter = None
                self.lt_filters = []

            def update(self, values):
                self.operation = "update"
                self.values = values
                return self

            def select(self, *columns):
                if self.operation is None:
                    self.operation = "select"
                return self

            def eq(self, column, value):
                self.filters.append((column, value))
                return self

            def in_(self, column, values):
                self.status_filter = (column, list(values))
                return self

            def lt(self, column, value):
                self.lt_filters.append((column, value))
                return self

            def limit(self, value):
                return self

            def execute(self):
                row = self.db.task
                for column, value in self.filters:
                    if row.get(column) != value:
                        return Response([])

                if self.operation == "select":
                    return Response([dict(row)])

                if self.operation == "update":
                    if self.status_filter:
                        column, allowed = self.status_filter
                        if row.get(column) not in allowed:
                            return Response([])
                    for column, cutoff in self.lt_filters:
                        value = row.get(column)
                        if value is None or value >= cutoff:
                            return Response([])
                    row.update(self.values)
                    return Response([dict(row)])

                return Response([])

        db = FakeDB()
        core = AgentCore(db, gemini_client=object())

        result = core.run_task("user-1", "task-2")

        self.assertEqual(result["status"], "running")
        self.assertEqual(db.task["status"], "running")


    def test_expired_lease_can_be_reclaimed_and_old_worker_is_fenced(self):
        from datetime import datetime, timezone, timedelta

        class Response:
            def __init__(self, data):
                self.data = data

        class FakeDB:
            def __init__(self):
                old_time = datetime.now(timezone.utc) - timedelta(minutes=20)
                self.task = {
                    "id": "task-expired",
                    "user_id": "user-1",
                    "goal": "test expired lease",
                    "status": "running",
                    "updated_at": old_time.isoformat(),
                    "lease_token": "old-token",
                    "plan": [],
                    "error": None,
                }

            def table(self, name):
                return FakeQuery(self, name)

        class FakeQuery:
            def __init__(self, db, name):
                self.db = db
                self.name = name
                self.operation = None
                self.values = {}
                self.filters = []
                self.status_filter = None
                self.lt_filters = []
                self.returning = False

            def update(self, values):
                self.operation = "update"
                self.values = dict(values)
                return self

            def select(self, *columns):
                if self.operation == "update":
                    self.returning = True
                else:
                    self.operation = "select"
                return self

            def eq(self, column, value):
                self.filters.append((column, value))
                return self

            def in_(self, column, values):
                self.status_filter = (column, list(values))
                return self

            def lt(self, column, value):
                self.lt_filters.append((column, value))
                return self

            def execute(self):
                if self.name != "agent_tasks":
                    return Response([])

                row = self.db.task

                for column, value in self.filters:
                    if row.get(column) != value:
                        return Response([])

                if self.status_filter:
                    column, allowed = self.status_filter
                    if row.get(column) not in allowed:
                        return Response([])

                for column, cutoff in self.lt_filters:
                    value = row.get(column)
                    if value is None or value >= cutoff:
                        return Response([])

                if self.operation == "select":
                    return Response([dict(row)])

                if self.operation == "update":
                    row.update(self.values)
                    return Response([dict(row)] if self.returning else [])

                return Response([])

        db = FakeDB()
        core = AgentCore(db, gemini_client=object())

        claimed = core._claim_task("task-expired", "user-1")

        self.assertIsNotNone(claimed)
        self.assertEqual(claimed["status"], "running")
        self.assertNotEqual(claimed["lease_token"], "old-token")
        self.assertEqual(db.task["lease_token"], claimed["lease_token"])

        with self.assertRaises(AgentCoreError):
            core._heartbeat("task-expired", "user-1", "old-token")

        with self.assertRaises(AgentCoreError):
            core._update_task(
                "task-expired",
                "user-1",
                {"status": "failed"},
                "old-token"
            )

        self.assertEqual(db.task["status"], "running")
        self.assertEqual(db.task["lease_token"], claimed["lease_token"])

    def test_resume_skips_completed_steps(self):
        from unittest.mock import patch

        class Response:
            def __init__(self, data=None):
                self.data = data or []

        class FakeDB:
            def __init__(self):
                self.tables = {
                    "agent_tasks": [{
                        "id": "task-resume",
                        "user_id": "user-1",
                        "goal": "test resume",
                        "status": "failed",
                        "plan": [
                            {"key": "step_1", "title": "Step 1",
                             "tool": "fake_tool", "input": {"n": 1}},
                            {"key": "step_2", "title": "Step 2",
                             "tool": "fake_tool", "input": {"n": 2}},
                        ],
                        "error": "temporary error",
                        "result": None,
                    }],
                    "agent_task_steps": [{
                        "task_id": "task-resume",
                        "step_key": "step_1",
                        "title": "Step 1",
                        "tool_name": "fake_tool",
                        "input": {"n": 1},
                        "output": {"value": "saved"},
                        "status": "completed",
                        "attempts": 1,
                    }],
                    "agent_task_events": [],
                }

            def table(self, name):
                return FakeQuery(self, name)

        class FakeQuery:
            def __init__(self, db, name):
                self.db = db
                self.name = name
                self.operation = None
                self.values = None
                self.filters = []
                self.status_filter = None
                self.lt_filters = []
                self.returning = False

            def select(self, *columns):
                if self.operation is None:
                    self.operation = "select"
                else:
                    self.returning = True
                return self

            def update(self, values):
                self.operation = "update"
                self.values = dict(values)
                return self

            def insert(self, values):
                self.operation = "insert"
                self.values = values
                return self

            def eq(self, column, value):
                self.filters.append((column, value))
                return self

            def in_(self, column, values):
                self.status_filter = (column, list(values))
                return self

            def lt(self, column, value):
                self.lt_filters.append((column, value))
                return self

            def limit(self, value):
                return self

            def execute(self):
                rows = self.db.tables[self.name]

                def matches(row):
                    for column, value in self.filters:
                        if row.get(column) != value:
                            return False
                    if self.status_filter:
                        column, allowed = self.status_filter
                        if row.get(column) not in allowed:
                            return False
                    for column, cutoff in self.lt_filters:
                        value = row.get(column)
                        if value is None or value >= cutoff:
                            return False
                    return True

                if self.operation == "select":
                    return Response([dict(row) for row in rows if matches(row)])

                if self.operation == "insert":
                    items = self.values if isinstance(self.values, list) else [self.values]
                    inserted = [dict(item) for item in items]
                    rows.extend(inserted)
                    return Response(inserted)

                if self.operation == "update":
                    updated = []
                    for row in rows:
                        if matches(row):
                            row.update(self.values)
                            updated.append(dict(row))
                    return Response(updated if self.returning else [])

                return Response()

        db = FakeDB()
        core = AgentCore(db, gemini_client=object())
        calls = []

        def fake_tool(data):
            calls.append(data["n"])
            return {"value": f"result-{data['n']}"}

        with patch.dict("agent_core.TOOL_REGISTRY", {"fake_tool": fake_tool}):
            result = core.run_task("user-1", "task-resume")

        self.assertEqual(calls, [2])
        self.assertEqual(result["status"], "completed")

        saved_steps = db.tables["agent_task_steps"]
        step_1 = next(row for row in saved_steps if row["step_key"] == "step_1")
        step_2 = next(row for row in saved_steps if row["step_key"] == "step_2")

        self.assertEqual(step_1["output"], {"value": "saved"})
        self.assertEqual(step_1["attempts"], 1)
        self.assertEqual(step_2["status"], "completed")
        self.assertEqual(step_2["output"], {"value": "result-2"})

if __name__ == "__main__":
    unittest.main()

class PeriodicHeartbeatTests(unittest.TestCase):
    def test_heartbeat_runs_repeatedly_during_tool_execution(self):
        import time
        from unittest.mock import patch

        core = AgentCore(object(), gemini_client=object())
        calls = []

        def fake_heartbeat(task_id, user_id, lease_token):
            calls.append(time.monotonic())

        core._heartbeat = fake_heartbeat

        with patch("agent_core.HEARTBEAT_SECONDS", 0.03):
            result = core._run_tool_with_heartbeat(
                lambda payload: (time.sleep(0.14) or {"ok": True}),
                {},
                "task-heartbeat",
                "user-1",
                "test-token",
            )

        self.assertEqual(result, {"ok": True})
        self.assertGreaterEqual(len(calls), 2)

    def test_lost_lease_during_tool_prevents_result_return(self):
        import time
        from unittest.mock import patch

        core = AgentCore(object(), gemini_client=object())

        def lost_lease(task_id, user_id, lease_token):
            raise AgentCoreError("Lease lost")

        core._heartbeat = lost_lease

        with patch("agent_core.HEARTBEAT_SECONDS", 0.01):
            with self.assertRaises(AgentCoreError):
                core._run_tool_with_heartbeat(
                    lambda payload: (time.sleep(0.06) or {"secret": "result"}),
                    {},
                    "task-lost",
                    "user-1",
                    "old-token",
                )



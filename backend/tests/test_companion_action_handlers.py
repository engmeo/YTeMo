from companion_action_handlers import make_clinician_review_handler, make_timeline_note_handler


class Query:
    def __init__(self, db, table):
        self.db, self.table = db, table
        self.payload = None
        self.filters = {}
    def insert(self, payload): self.payload = payload; return self
    def select(self, *_): return self
    def eq(self, key, value): self.filters[key] = value; return self
    def limit(self, _): return self
    def execute(self):
        rows = self.db.tables.setdefault(self.table, [])
        if self.payload is not None:
            if any(row.get("action_task_id") == self.payload.get("action_task_id") for row in rows):
                raise RuntimeError("duplicate action task")
            row = {"id": f"{self.table}-{len(rows)+1}", **self.payload}
            rows.append(row)
            return type("Result", (), {"data": [row]})()
        matches = [row for row in rows if all(row.get(k) == v for k, v in self.filters.items())]
        return type("Result", (), {"data": matches[:1]})()


class FakeDB:
    def __init__(self): self.tables = {}
    def table(self, name): return Query(self, name)


def test_clinician_review_request_is_persisted_idempotently():
    db = FakeDB()
    handler = make_clinician_review_handler(db)
    args = {"reason": "Cần bác sĩ xem xét kết quả", "_action_task_id": "task-1"}
    first = handler("owner-1", args)
    second = handler("owner-1", args)
    assert first["id"] == second["id"]
    assert first["human_review_required"] is True
    assert len(db.tables["companion_needs"]) == 1


def test_timeline_note_preserves_source_and_is_idempotent():
    db = FakeDB()
    handler = make_timeline_note_handler(db)
    args = {"note": "Người dùng báo đã tái khám", "source": "Người dùng nhập", "_action_task_id": "task-2"}
    first = handler("owner-1", args)
    second = handler("owner-1", args)
    assert first["id"] == second["id"]
    event = db.tables["companion_events"][0]
    assert event["payload"]["source"] == "Người dùng nhập"
    assert event["event_type"] == "TIMELINE_NOTE_ADDED"

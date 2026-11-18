import unittest
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from companion_core import (
    CompanionState, ConsentRecord, ConsentScope, ContextItem,
    SupportNeed, NeedStatus, UserPriority, CompanionEvent,
)
from supabase_companion_repository import SupabaseCompanionRepository


class Result:
    def __init__(self, data=None): self.data = data or []


class FakeDB:
    def __init__(self):
        self.rows = {name: [] for name in (
            "companion_consents", "companion_context", "companion_needs", "companion_events"
        )}
        self.operations = []
    def table(self, name): return Query(self, name)


class Query:
    def __init__(self, db, table):
        self.db, self.name = db, table
        self.filters, self.action, self.payload = [], "select", None
        self.conflict = None
    def select(self, *_): self.action="select"; return self
    def eq(self, k, v): self.filters.append((k,v)); return self
    def is_(self, k, v): self.filters.append((k,None if v=="null" else v)); return self
    def order(self, *_a, **_kw): return self
    def limit(self, *_): return self
    def upsert(self, payload, on_conflict=None): self.action="upsert"; self.payload=payload; self.conflict=on_conflict; return self
    def insert(self, payload): self.action="insert"; self.payload=payload; return self
    def update(self, payload): self.action="update"; self.payload=payload; return self
    def _matches(self, row): return all(row.get(k)==v for k,v in self.filters)
    def execute(self):
        rows=self.db.rows[self.name]
        matched=[r for r in rows if self._matches(r)]
        self.db.operations.append((self.name,self.action,deepcopy(self.payload),list(self.filters)))
        if self.action=="select": return Result(deepcopy(matched))
        if self.action=="upsert":
            key_fields=self.conflict.split(",") if self.conflict else ["id"]
            old=next((r for r in rows if all(r.get(k)==self.payload.get(k) for k in key_fields)),None)
            if old: old.update(deepcopy(self.payload))
            else: rows.append(deepcopy(self.payload))
            return Result([deepcopy(old or rows[-1])])
        if self.action=="insert":
            rows.append(deepcopy(self.payload)); return Result([deepcopy(self.payload)])
        if self.action=="update":
            for r in matched: r.update(deepcopy(self.payload))
            return Result(deepcopy(matched))
        return Result()


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.db=FakeDB(); self.repo=SupabaseCompanionRepository(self.db)
        self.uid="user-1"

    def test_user_filter_applied_to_every_read(self):
        self.repo.get(self.uid)
        reads=[op for op in self.db.operations if op[1]=="select"]
        self.assertEqual(len(reads),4)
        for _,_,_,filters in reads: self.assertIn(("user_id",self.uid),filters)

    def test_save_only_writes_changed_rows(self):
        state=CompanionState(user_id=self.uid)
        self.repo.get(self.uid)
        state.events.append(CompanionEvent(str(uuid4()),self.uid,"init","ok","2026-01-01T00:00:00+00:00"))
        self.repo.save(state)
        writes=[op for op in self.db.operations if op[1] in ("upsert","insert","update")]
        self.assertEqual(len(writes),1)
        self.assertEqual(writes[0][0],"companion_events")

    def test_context_delete_only_targets_removed_snapshot_id(self):
        cid=str(uuid4())
        self.db.rows["companion_context"].append({
            "id":cid,"user_id":self.uid,"scope":"HEALTH_CONTEXT",
            "context_type":"note","content":{"text":"x"},"created_at":"t",
            "deleted_at":None
        })
        state=self.repo.get(self.uid)
        self.assertEqual(len(state.context_items),1)
        state.context_items=[]
        self.repo.save(state)
        updates=[op for op in self.db.operations if op[0]=="companion_context" and op[1]=="update"]
        self.assertEqual(len(updates),1)
        self.assertIn(("user_id",self.uid),updates[0][3])
        self.assertIn(("id",cid),updates[0][3])

    def test_stale_snapshot_does_not_delete_concurrent_new_context(self):
        stale=self.repo.get(self.uid) or CompanionState(user_id=self.uid)
        # Simulate another request inserting a row after this request read.
        concurrent_id=str(uuid4())
        self.db.rows["companion_context"].append({
            "id":concurrent_id,"user_id":self.uid,"scope":"HEALTH_CONTEXT",
            "context_type":"note","content":{"text":"new"},"created_at":"t",
            "deleted_at":None
        })
        stale.events.append(CompanionEvent(str(uuid4()),self.uid,"init","ok","t"))
        self.repo.save(stale)
        self.assertIsNone(self.db.rows["companion_context"][0].get("deleted_at"))
        self.assertFalse(any(op[0]=="companion_context" and op[1]=="update" for op in self.db.operations))

    def test_consent_upsert_uses_user_scope_conflict_key(self):
        state=CompanionState(user_id=self.uid)
        self.repo.get(self.uid)
        state.consents[ConsentScope.HEALTH_CONTEXT.value]=ConsentRecord(
            ConsentScope.HEALTH_CONTEXT,True,"2026-01-01T00:00:00+00:00")
        self.repo.save(state)
        op=next(op for op in self.db.operations if op[0]=="companion_consents" and op[1]=="upsert")
        self.assertEqual(op[1],"upsert")
        self.assertEqual(op[2]["scope"],"HEALTH_CONTEXT")


if __name__=="__main__": unittest.main()

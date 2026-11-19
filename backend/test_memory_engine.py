import unittest
from copy import deepcopy

from memory_engine import MemoryEngine, MemoryQuery, _is_temporally_valid


class InMemoryRepo:
    def __init__(self):
        self.rows = []
        self.logs = []

    def insert(self, row):
        saved = deepcopy(row)
        self.rows.append(saved)
        return saved

    def insert_with_audit(self, row, audit):
        saved = deepcopy(row)
        audit_row = deepcopy(audit)
        audit_row["memory_id"] = saved["id"]
        # Stage both records before mutating repository state.
        self.rows.append(saved)
        self.logs.append(audit_row)
        return saved

    def find_duplicate(self, *, user_id, agent_key, memory_type, dedupe_hash):
        for row in self.rows:
            if (row["owner_type"] == "USER" and row["user_id"] == user_id
                and row.get("agent_key") == agent_key
                and row["memory_type"] == memory_type
                and row["dedupe_hash"] == dedupe_hash
                and row["status"] in {"CANDIDATE", "ACTIVE"}
                and not row.get("deleted_at")):
                return row
        return None

    def retrieve(self, *, user_id, agent_key, memory_types, as_of,
                 include_agent_global, limit):
        result = []
        for row in self.rows:
            if row.get("deleted_at") or row["status"] != "ACTIVE":
                continue
            if row["owner_type"] == "USER":
                if row.get("user_id") != user_id:
                    continue
                if row.get("agent_key") not in (None, agent_key):
                    continue
            elif not (include_agent_global and row["owner_type"] == "AGENT"
                      and row.get("agent_key") == agent_key):
                continue
            if memory_types and row["memory_type"] not in memory_types:
                continue
            if not _is_temporally_valid(row, as_of):
                continue
            result.append(row)
        return sorted(result, key=lambda x: x.get("recorded_at", ""), reverse=True)[:limit]

    def update(self, memory_id, values, *, user_id, expected_status=None):
        for row in self.rows:
            if (row["id"] == memory_id
                    and row.get("owner_type") == "USER"
                    and row.get("user_id") == user_id
                    and not row.get("deleted_at")
                    and (expected_status is None or row.get("status") == expected_status)):
                row.update(values)
                return deepcopy(row)
        raise LookupError("Memory not found or owner scope mismatch")

    def update_with_audit(self, memory_id, values, audit, *,
                          user_id, expected_status=None):
        for row in self.rows:
            if (row["id"] == memory_id
                    and row.get("owner_type") == "USER"
                    and row.get("user_id") == user_id
                    and not row.get("deleted_at")
                    and (expected_status is None
                         or row.get("status") == expected_status)):
                staged = deepcopy(row)
                staged.update(deepcopy(values))
                audit_row = deepcopy(audit)
                audit_row["memory_id"] = memory_id
                # If audit staging fails, the memory row remains unchanged.
                self.logs.append(audit_row)
                row.update(staged)
                return deepcopy(row)
        raise LookupError("Memory not found or update not permitted")

    def audit(self, row):
        self.logs.append(deepcopy(row))


class MemoryEngineTests(unittest.TestCase):
    def setUp(self):
        self.repo = InMemoryRepo()
        self.engine = MemoryEngine(self.repo, lambda user, scope: scope == "BASIC_PROFILE")

    def write_user(self, user="u1", **kwargs):
        args = dict(
            owner_type="USER", user_id=user, memory_type="EPISODIC",
            content={"event": "visited clinic"}, summary="Clinic visit",
            source_type="USER_INPUT", sensitivity="NORMAL",
        )
        args.update(kwargs)
        return self.engine.write(**args)

    def test_write_defaults_to_candidate_unverified(self):
        result = self.write_user()
        self.assertTrue(result.created)
        self.assertEqual(result.record.status, "CANDIDATE")
        self.assertEqual(result.record.verification_state, "UNVERIFIED")

    def test_duplicate_is_not_inserted_twice(self):
        self.write_user()
        second = self.write_user()
        self.assertFalse(second.created)
        self.assertEqual(len(self.repo.rows), 1)

    def test_user_isolation_on_retrieval(self):
        self.write_user(user="u1")
        self.write_user(user="u2", content={"event": "different"}, summary="Other")
        self.engine.review(self.repo.rows[0]["id"], user_id="u1", decision="APPROVE", actor_id="reviewer")
        found = self.engine.retrieve(MemoryQuery(user_id="u1"))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].user_id, "u1")

    def test_health_memory_requires_consent(self):
        with self.assertRaises(PermissionError):
            self.write_user(sensitivity="HEALTH", consent_scope="HEALTH_CONTEXT")

    def test_consent_scope_is_checked(self):
        result = self.write_user(sensitivity="PERSONAL", consent_scope="BASIC_PROFILE")
        self.assertTrue(result.created)

    def test_agent_cannot_review_own_memory(self):
        item = self.write_user().record
        with self.assertRaises(PermissionError):
            self.engine.review(item.id, user_id="u1", decision="APPROVE", actor_id="agent-x", actor_type="AGENT")

    def test_approved_memory_becomes_retrievable(self):
        item = self.write_user().record
        self.engine.review(item.id, user_id="u1", decision="APPROVE", actor_id="human-reviewer")
        self.assertEqual(len(self.engine.retrieve(MemoryQuery(user_id="u1"))), 1)

    def test_soft_deleted_memory_is_not_retrieved(self):
        item = self.write_user().record
        self.engine.review(item.id, user_id="u1", decision="APPROVE", actor_id="human-reviewer")
        self.engine.soft_delete(item.id, user_id="u1", actor_id="human-reviewer")
        self.assertEqual(self.engine.retrieve(MemoryQuery(user_id="u1")), [])
        self.assertEqual(self.repo.logs[-1]["action"], "DELETED")

    def test_review_cannot_review_memory_twice(self):
        item = self.write_user().record
        self.engine.review(
            item.id, user_id="u1", decision="APPROVE",
            actor_id="human-reviewer",
        )
        with self.assertRaises(LookupError):
            self.engine.review(
                item.id, user_id="u1", decision="REJECT",
                actor_id="human-reviewer",
            )

    def test_review_rejects_wrong_memory_owner(self):
        item = self.write_user(user="u1").record
        with self.assertRaises(LookupError):
            self.engine.review(
                item.id, user_id="u2", decision="APPROVE",
                actor_id="human-reviewer",
            )
        self.assertEqual(self.repo.rows[0]["status"], "CANDIDATE")

    def test_temporal_null_start_is_unbounded(self):
        self.assertTrue(_is_temporally_valid(
            {"valid_from": None},
            "2026-11-19T10:00:00+00:00",
        ))

    def test_temporal_expiry_at_exact_time_is_expired(self):
        moment = "2026-11-19T10:00:00+00:00"
        self.assertFalse(_is_temporally_valid(
            {"valid_until": moment}, moment,
        ))
        self.assertFalse(_is_temporally_valid(
            {"expires_at": moment}, moment,
        ))

    def test_temporal_offsets_are_compared_as_instants(self):
        self.assertFalse(_is_temporally_valid(
            {"valid_until": "2026-11-19T12:00:00+02:00"},
            "2026-11-19T10:00:00Z",
        ))

    def test_temporal_malformed_timestamp_fails_closed(self):
        self.assertFalse(_is_temporally_valid(
            {"valid_from": "not-a-date"},
            "2026-11-19T10:00:00Z",
        ))
        self.assertFalse(_is_temporally_valid(
            {"expires_at": "not-a-date"},
            "2026-11-19T10:00:00Z",
        ))

    def test_confidence_range(self):
        with self.assertRaises(ValueError):
            self.write_user(confidence=1.5)


if __name__ == "__main__":
    unittest.main()


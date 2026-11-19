import unittest
from datetime import datetime, timedelta, timezone

from temporal_memory import (
    TemporalMemory, TemporalMemoryQuery, VersionConflictError,
    VersionedMemoryStore,
)

UTC = timezone.utc


def item(value="old", owner="u1", start=None, end=None):
    return TemporalMemory(
        memory_id="m1", owner_id=owner, subject_key="patient:1",
        predicate="care_preference", value=value,
        valid_from=start, valid_until=end,
    )


class TemporalMemoryTests(unittest.TestCase):
    def setUp(self):
        self.store = VersionedMemoryStore()
        self.v1 = self.store.create(item(), "human-1", "initial capture")

    def test_create_first_version(self):
        self.assertEqual(self.v1.version_number, 1)

    def test_revisions_are_append_only(self):
        v2 = self.store.revise(item("new"), "human-1", "user correction")
        self.assertEqual(v2.version_number, 2)
        self.assertEqual([v.version_number for v in self.store.history("m1", "u1")], [1, 2])

    def test_stale_revision_rejected(self):
        with self.assertRaises(VersionConflictError):
            self.store.revise(item("new"), "human-1", "stale update", expected_version=0)

    def test_owner_cannot_be_changed(self):
        with self.assertRaises(PermissionError):
            self.store.revise(item("new", owner="u2"), "human-1", "owner change")

    def test_cross_user_history_hidden(self):
        self.assertEqual(self.store.history("m1", "u2"), [])
        self.assertIsNone(self.store.get_current("m1", "u2"))

    def test_restore_creates_new_version(self):
        self.store.revise(item("new"), "human-1", "correction")
        v3 = self.store.restore_as_new_version("m1", "u1", 1, "human-1", "restore prior")
        self.assertEqual(v3.version_number, 3)
        self.assertEqual(self.store.get_current("m1", "u1").value, "old")

    def test_valid_at_respects_half_open_interval(self):
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2025, 1, 1, tzinfo=UTC)
        m = item("value", start=start, end=end)
        self.assertEqual(len(TemporalMemoryQuery.valid_at([m], start, "u1")), 1)
        self.assertEqual(TemporalMemoryQuery.valid_at([m], end, "u1"), [])

    def test_valid_at_filters_owner(self):
        self.assertEqual(TemporalMemoryQuery.valid_at([item(owner="u2")], datetime.now(UTC), "u1"), [])

    def test_valid_at_ignores_non_active(self):
        m = TemporalMemory("m2", "u1", "p", "x", "v", status="SUPERSEDED")
        self.assertEqual(TemporalMemoryQuery.valid_at([m], datetime.now(UTC), "u1"), [])

    def test_known_at_filters_future_versions(self):
        versions = self.store.history("m1", "u1")
        before = versions[0].recorded_at - timedelta(seconds=1)
        self.assertEqual(TemporalMemoryQuery.known_at(versions, before), [])
        self.assertEqual(len(TemporalMemoryQuery.known_at(versions, versions[0].recorded_at)), 1)

    def test_invalid_validity_window_rejected(self):
        t = datetime(2025, 1, 1, tzinfo=UTC)
        with self.assertRaises(ValueError):
            item(start=t, end=t)

    def test_change_requires_actor_and_reason(self):
        with self.assertRaises(ValueError):
            self.store.revise(item("new"), "", "reason")


if __name__ == "__main__":
    unittest.main()

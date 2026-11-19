import unittest
from datetime import datetime, timezone

from memory_conflict_engine import (
    ClaimStatus, ConflictDetector, Evidence, EvidenceStore,
    MemoryClaim, MemoryConflictEngine,
)

UTC = timezone.utc


def claim(mid, value, owner="u1", start=None, end=None, status=ClaimStatus.ACTIVE):
    return MemoryClaim(
        memory_id=mid, owner_id=owner, subject_key="patient:1",
        predicate="allergy:drug_a", value=value,
        valid_from=start, valid_until=end, status=status,
    )


class ConflictEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = MemoryConflictEngine()

    def test_different_values_same_time_conflict(self):
        result = self.engine.detect_conflicts([claim("a", True), claim("b", False)])
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].requires_human_review)

    def test_same_value_no_conflict(self):
        self.assertEqual(self.engine.detect_conflicts([claim("a", "yes"), claim("b", "yes")]), [])

    def test_different_users_are_isolated(self):
        self.assertEqual(self.engine.detect_conflicts([
            claim("a", True, "u1"), claim("b", False, "u2")
        ]), [])

    def test_non_overlapping_periods_are_not_conflict(self):
        t1 = datetime(2020, 1, 1, tzinfo=UTC)
        t2 = datetime(2021, 1, 1, tzinfo=UTC)
        t3 = datetime(2022, 1, 1, tzinfo=UTC)
        self.assertEqual(self.engine.detect_conflicts([
            claim("a", True, start=t1, end=t2),
            claim("b", False, start=t2, end=t3),
        ]), [])

    def test_overlapping_periods_conflict(self):
        t1 = datetime(2020, 1, 1, tzinfo=UTC)
        t2 = datetime(2021, 1, 1, tzinfo=UTC)
        t3 = datetime(2022, 1, 1, tzinfo=UTC)
        self.assertEqual(len(self.engine.detect_conflicts([
            claim("a", True, start=t1, end=t3),
            claim("b", False, start=t2),
        ])), 1)

    def test_retracted_claim_is_ignored(self):
        self.assertEqual(self.engine.detect_conflicts([
            claim("a", True, status=ClaimStatus.RETRACTED),
            claim("b", False),
        ]), [])

    def test_missing_record_is_not_negative_claim(self):
        # Detector only compares explicit claims; absence never creates a false value.
        self.assertEqual(self.engine.detect_conflicts([claim("a", True)]), [])

    def test_evidence_provenance_is_returned(self):
        evidence = Evidence.from_source(
            "clinical_record", "record-123", "Prior visit",
            excerpt="Allergy documented",
        )
        self.engine.attach_evidence(evidence)
        c = MemoryClaim(
            memory_id="m1", owner_id="u1", subject_key="patient:1",
            predicate="allergy:drug_a", value=True,
            evidence_ids=(evidence.evidence_id,),
        )
        detail = self.engine.explain_claim(c)
        self.assertEqual(detail["evidence"][0]["source_ref"], "record-123")
        self.assertTrue(detail["evidence"][0]["excerpt_hash"])

    def test_evidence_deduplicates(self):
        store = EvidenceStore()
        a = Evidence.from_source("user_statement", "chat-1", excerpt="said yes")
        b = Evidence.from_source("user_statement", "chat-1", excerpt="said yes")
        store.add(a)
        store.add(b)
        self.assertEqual(store.get(a.evidence_id), b)

    def test_invalid_time_range_rejected(self):
        t = datetime(2022, 1, 1, tzinfo=UTC)
        with self.assertRaises(ValueError):
            claim("a", True, start=t, end=t)


if __name__ == "__main__":
    unittest.main()

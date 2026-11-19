import unittest
from datetime import datetime, timedelta, timezone

from memory_intelligence import (
    DerivedMemory, DerivationGraph, HybridMemoryRetriever,
    MemoryConsolidator, RetrievalDocument,
)

UTC = timezone.utc


class MemoryIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.graph = DerivationGraph()
        self.graph.register_source("s1", "u1")
        self.graph.register_source("s2", "u1")

    def test_add_derived_memory(self):
        item = DerivedMemory("d1", "u1", "summary", ("s1", "s2"), "rule", "agent-a")
        self.graph.add_derivation(item)
        self.assertEqual(self.graph.get_derived("d1", "u1"), item)

    def test_lineage_returns_sources(self):
        self.graph.add_derivation(DerivedMemory("d1", "u1", "summary", ("s1", "s2"), "rule", "agent-a"))
        self.assertEqual(self.graph.lineage("d1", "u1"), ["s1", "s2"])

    def test_cross_owner_source_rejected(self):
        self.graph.register_source("s3", "u2")
        with self.assertRaises(PermissionError):
            self.graph.add_derivation(DerivedMemory("d1", "u1", "summary", ("s3",), "rule", "agent-a"))

    def test_unknown_source_rejected(self):
        with self.assertRaises(PermissionError):
            self.graph.add_derivation(DerivedMemory("d1", "u1", "summary", ("missing",), "rule", "agent-a"))

    def test_duplicate_derived_id_rejected(self):
        d = DerivedMemory("d1", "u1", "summary", ("s1",), "rule", "agent-a")
        self.graph.add_derivation(d)
        with self.assertRaises(ValueError):
            self.graph.add_derivation(d)

    def test_lineage_hidden_from_other_owner(self):
        self.graph.add_derivation(DerivedMemory("d1", "u1", "summary", ("s1",), "rule", "agent-a"))
        self.assertEqual(self.graph.lineage("d1", "u2"), [])

    def test_exact_duplicate_candidates_same_owner(self):
        rows = [
            {"memory_id": "m1", "owner_id": "u1", "content": "Known allergy"},
            {"memory_id": "m2", "owner_id": "u1", "content": " known   ALLERGY "},
            {"memory_id": "m3", "owner_id": "u2", "content": "Known allergy"},
        ]
        candidates = MemoryConsolidator().find_duplicates(rows)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].memory_ids, ("m1", "m2"))
        self.assertTrue(candidates[0].requires_review)

    def test_expired_memory_candidate(self):
        now = datetime.now(UTC)
        rows = [{"memory_id": "m1", "owner_id": "u1", "expires_at": now - timedelta(days=1)}]
        found = MemoryConsolidator().find_expired(rows, now)
        self.assertEqual(found[0].suggested_action, "REVIEW_FOR_ARCHIVE")

    def test_retrieval_matches_terms(self):
        docs = [RetrievalDocument("m1", "u1", "patient prefers morning appointment")]
        hits = HybridMemoryRetriever().search(docs, "morning appointment", "u1")
        self.assertEqual(hits[0].document.memory_id, "m1")

    def test_retrieval_isolates_users(self):
        docs = [
            RetrievalDocument("m1", "u1", "drug allergy"),
            RetrievalDocument("m2", "u2", "drug allergy"),
        ]
        hits = HybridMemoryRetriever().search(docs, "drug allergy", "u1")
        self.assertEqual([h.document.memory_id for h in hits], ["m1"])

    def test_retrieval_filters_status_and_type(self):
        docs = [
            RetrievalDocument("m1", "u1", "care plan", status="ARCHIVED"),
            RetrievalDocument("m2", "u1", "care plan", memory_type="EPISODIC"),
        ]
        hits = HybridMemoryRetriever().search(docs, "care plan", "u1", memory_types={"SEMANTIC"})
        self.assertEqual(hits, [])

    def test_retrieval_respects_validity(self):
        now = datetime.now(UTC)
        docs = [RetrievalDocument("m1", "u1", "care plan", valid_until=now - timedelta(seconds=1))]
        self.assertEqual(HybridMemoryRetriever().search(docs, "care plan", "u1", as_of=now), [])

    def test_retrieval_empty_query(self):
        self.assertEqual(HybridMemoryRetriever().search([], "   ", "u1"), [])

    def test_retrieval_requires_owner_and_positive_limit(self):
        retriever = HybridMemoryRetriever()
        with self.assertRaises(ValueError):
            retriever.search([], "query", "")
        with self.assertRaises(ValueError):
            retriever.search([], "query", "u1", limit=0)


if __name__ == "__main__":
    unittest.main()

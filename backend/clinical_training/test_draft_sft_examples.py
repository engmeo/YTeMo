import unittest

from draft_sft_examples import build_examples


class DraftSftExamplesTests(unittest.TestCase):
    def test_builds_evidence_state_drafts_without_auto_approval(self):
        for state in ("STRONG", "WEAK", "CONFLICTING", "INSUFFICIENT"):
            claim = {
                "claim_id": f"CL-{state}",
                "claim_summary": "Nội dung claim giả lập.",
                "evidence_state": state,
                "source_id": "SRC-001",
                "source_url": "https://example.org/source",
                "license": "CC-BY-4.0",
                "population": "Người trưởng thành",
                "source_verified": True,
            }
            rows = build_examples(claim)
            self.assertEqual(len(rows), 2)
            self.assertTrue(all(row["clinical_review_status"] == "DRAFT" for row in rows))
            self.assertTrue(all(row["privacy_reviewed"] is False for row in rows))
            self.assertTrue(all(row["evidence_state"] == state for row in rows))

    def test_rejects_missing_provenance(self):
        with self.assertRaises(ValueError):
            build_examples({"claim_id": "x", "evidence_state": "STRONG"})


if __name__ == "__main__":
    unittest.main()

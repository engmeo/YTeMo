import unittest

from clinical_evidence_intelligence import lexical_score, reciprocal_rank_fusion, vector_literal, DIMENSIONS


class ClinicalEvidenceIntelligenceTests(unittest.TestCase):
    def test_lexical_score_is_bounded(self):
        self.assertEqual(lexical_score("blood pressure adult", "adult blood pressure"), 1.0)
        self.assertEqual(lexical_score("unrelated", "blood pressure"), 0.0)

    def test_rrf_combines_rankings(self):
        fused = reciprocal_rank_fusion(
            [{"claim_id": "a"}, {"claim_id": "b"}],
            [{"claim_id": "b"}, {"claim_id": "a"}],
        )
        self.assertEqual({x["claim_id"] for x in fused}, {"a", "b"})
        self.assertAlmostEqual(fused[0]["rrf_score"], fused[1]["rrf_score"])

    def test_vector_literal_dimension_guard(self):
        with self.assertRaises(ValueError):
            vector_literal([0.1])
        self.assertTrue(vector_literal([0.0] * DIMENSIONS).startswith("["))


if __name__ == "__main__":
    unittest.main()

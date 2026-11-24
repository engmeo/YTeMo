import unittest

from clinical_knowledge_evaluation import evaluate_case, evaluate_dataset


class ClinicalKnowledgeEvaluationTests(unittest.TestCase):
    def test_case_scores_claim_and_citation_against_gold(self):
        case = {
            "case_id": "gold-1",
            "expected_claim_ids": ["claim-1"],
            "forbidden_claim_ids": ["claim-2"],
            "expected_abstention": False,
            "expected_citations": [{
                "claim_id": "claim-1", "document_id": "doc-1", "version": "v1", "page": 3,
                "exact_quote": "An exact source quotation.",
                "source_url": "https://official.example/guideline.pdf",
            }],
        }
        result = {
            "abstention": False,
            "evidence": [{
                "claim": {"id": "claim-1"},
                "document": {"id": "doc-1", "version": "v1"},
                "citation": {
                    "page": 3, "exact_quote": "An exact source quotation.",
                    "source_url": "https://official.example/guideline.pdf",
                },
            }],
        }
        scored = evaluate_case(case, result)
        self.assertEqual(scored["precision_at_k"], 1.0)
        self.assertEqual(scored["recall_at_k"], 1.0)
        self.assertEqual(scored["citation_correctness"], 1.0)
        self.assertTrue(scored["abstention_correct"])
        self.assertEqual(scored["forbidden_claim_ids_returned"], [])

    def test_dataset_excludes_cases_without_two_verified_reviewers(self):
        cases = [
            {
                "case_id": "adjudicated",
                "adjudication_status": "ADJUDICATED",
                "expert_reviews": [
                    {"reviewer_id": "r1", "credential_verified": True, "decision": "ADJUDICATED_INPUT"},
                    {"reviewer_id": "r2", "credential_verified": True, "decision": "ADJUDICATED_INPUT"},
                ],
                "expected_claim_ids": [], "expected_abstention": True,
            },
            {
                "case_id": "template",
                "adjudication_status": "TEMPLATE_ONLY",
                "expert_reviews": [],
                "expected_claim_ids": [], "expected_abstention": True,
            },
        ]
        report = evaluate_dataset(cases, {"adjudicated": {"abstention": True, "evidence": []}})
        self.assertEqual(report["eligible_case_count"], 1)
        self.assertEqual(report["excluded_case_ids"], ["template"])
        self.assertEqual(report["metrics"]["abstention_accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()

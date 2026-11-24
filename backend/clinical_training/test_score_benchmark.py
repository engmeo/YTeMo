import json
import tempfile
import unittest
from pathlib import Path

from score_benchmark import score


class BenchmarkScoringTests(unittest.TestCase):
    def test_unblinds_only_after_two_independent_reviewers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blinded = root / "blind.jsonl"
            key = root / "key.jsonl"
            reviews = root / "reviews.jsonl"
            blinded.write_text(json.dumps({
                "case_id": "C1", "scenario_group": "insufficient_information",
                "model_a": {"text": "A"}, "model_b": {"text": "B"}
            }) + "\n", encoding="utf-8")
            key.write_text(json.dumps({
                "case_id": "C1", "model_a": "base", "model_b": "fine_tuned"
            }) + "\n", encoding="utf-8")
            values = {
                "clinical_correctness": 2, "evidence_state_handling": 2,
                "contextual_reasoning": 1, "citation_quality": 1,
                "safe_abstention": 2, "harmful_advice": 0,
            }
            reviews.write_text(json.dumps({
                "case_id": "C1",
                "reviewers": [
                    {"reviewer_id": "R1", "independence_verified": True, "model_a": values, "model_b": values},
                    {"reviewer_id": "R2", "independence_verified": True, "model_a": values, "model_b": values},
                ],
            }) + "\n", encoding="utf-8")
            report = score(blinded, key, reviews)
            self.assertEqual(report["cases_scored"], 1)
            self.assertEqual(report["models"]["base"]["clinical_correctness"], 2.0)
            self.assertEqual(report["release_status"], "NOT_CLINICALLY_VALIDATED")

    def test_skips_case_without_two_independent_reviewers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blinded, key, reviews = root / "b", root / "k", root / "r"
            blinded.write_text(json.dumps({"case_id":"C1","scenario_group":"x"})+"\n",encoding="utf-8")
            key.write_text(json.dumps({"case_id":"C1","model_a":"base","model_b":"fine_tuned"})+"\n",encoding="utf-8")
            reviews.write_text(json.dumps({"case_id":"C1","reviewers":[]})+"\n",encoding="utf-8")
            self.assertEqual(score(blinded,key,reviews)["cases_scored"],0)


if __name__ == "__main__":
    unittest.main()

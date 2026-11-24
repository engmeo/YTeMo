import json
import tempfile
import unittest
from pathlib import Path

from prepare_dataset import prepare


class ClinicalDatasetPreparationTests(unittest.TestCase):
    def test_accepts_reviewed_licensed_record_and_rejects_duplicate(self):
        record = {
            "instruction": "Giải thích huyết áp",
            "input": "Người trưởng thành hỏi về chỉ số huyết áp.",
            "response": "Giải thích giới hạn và khuyến nghị đo đúng cách.",
            "evidence_state": "STRONG",
            "source_id": "SRC-001",
            "source_url": "https://example.org/source",
            "license": "CC-BY-4.0",
            "clinical_review_status": "APPROVED_FOR_TRAINING",
            "clinical_review_id": "REV-001",
            "reviewer_count": 2,
            "privacy_reviewed": True,
            "source_verified": True,
            "contains_patient_data": False,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.jsonl"
            output_path = root / "out.jsonl"
            rejects_path = root / "rejects.jsonl"
            input_path.write_text(
                json.dumps(record, ensure_ascii=False) + "\n" +
                json.dumps(record, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            result = prepare(input_path, output_path, rejects_path, {"CC-BY-4.0"})
            self.assertEqual(result["accepted"], 1)
            self.assertEqual(result["deduplicated"], 1)
            output = json.loads(output_path.read_text(encoding="utf-8").strip())
            self.assertEqual(output["evidence_state"], "STRONG")
            self.assertEqual(output["source_id"], "SRC-001")

    def test_rejects_unlicensed_or_unreviewed_records(self):
        record = {
            "instruction": "Test", "response": "Test", "source_id": "x",
            "source_url": "https://example.org", "license": "UNKNOWN",
            "evidence_state": "WEAK", "clinical_review_status": "DRAFT",
            "privacy_reviewed": False, "source_verified": False,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, output, rejects = root / "in.jsonl", root / "out.jsonl", root / "rejects.jsonl"
            source.write_text(json.dumps(record) + "\n", encoding="utf-8")
            result = prepare(source, output, rejects, {"CC0-1.0"})
            self.assertEqual(result["accepted"], 0)
            self.assertEqual(result["rejected"], 1)


if __name__ == "__main__":
    unittest.main()

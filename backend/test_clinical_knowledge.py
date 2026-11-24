import unittest
from pydantic import ValidationError
from clinical_knowledge import (
    KnowledgeDocumentCreate, automated_document_checks, host_is_within,
    normalize_host, initial_document_status, is_reviewable_status,
    reviewer_is_independent,
)

class ClinicalKnowledgeChecksTests(unittest.TestCase):
    def test_official_host_match_is_boundary_safe(self):
        self.assertTrue(host_is_within("www.moh.gov.vn", "moh.gov.vn"))
        self.assertFalse(host_is_within("moh.gov.vn.attacker.example", "moh.gov.vn"))
    def test_normalize_host(self):
        self.assertEqual(normalize_host("https://www.who.int/publications"), "who.int")
    def test_missing_metadata_fails_closed(self):
        result = automated_document_checks({})
        self.assertFalse(result["passed"])
        self.assertIn("MISSING_TITLE", result["issues"])
        self.assertFalse(result["clinical_approval"])
    def test_integrity_pass_is_not_clinical_approval(self):
        metadata = {"title":"Guideline","publisher":"MoH","document_type":"guideline","source_url":"https://moh.gov.vn/doc","published_at":"2025-01-01","knowledge_domain":"national_guidelines","jurisdiction":"VN","target_population":"Adults"}
        result = automated_document_checks(metadata, "A" * 250)
        self.assertTrue(result["passed"])
        self.assertEqual(result["scope"], "metadata_and_extraction_integrity_only")
        self.assertFalse(result["clinical_approval"])
    def test_registered_host_and_clean_extraction_do_not_authenticate_document(self):
        self.assertEqual(initial_document_status(True, True), "DISCOVERED")
        self.assertEqual(initial_document_status(False, True), "DISCOVERED")
    def test_missing_jurisdiction_and_population_fail_closed(self):
        metadata = {"title":"Guideline","publisher":"MoH","document_type":"guideline","source_url":"https://moh.gov.vn/doc","published_at":"2025"}
        result = automated_document_checks(metadata, "A" * 250)
        self.assertFalse(result["passed"])
        self.assertIn("MISSING_JURISDICTION", result["issues"])
        self.assertIn("MISSING_TARGET_POPULATION", result["issues"])
    def test_document_requires_full_iso_publication_date(self):
        payload = {
            "title": "Clinical guideline", "publisher": "MoH", "document_type": "guideline",
            "source_url": "https://moh.gov.vn/document", "published_at": "2025",
            "knowledge_domain": "national_guidelines", "jurisdiction": "VN",
            "target_population": "Adults",
        }
        with self.assertRaises(ValidationError):
            KnowledgeDocumentCreate(**payload)
    def test_document_accepts_valid_provenance_dates(self):
        payload = {
            "title": "Clinical guideline", "publisher": "MoH", "document_type": "guideline",
            "source_url": "https://moh.gov.vn/document", "published_at": "2025-01-15",
            "effective_from": "2025-02-01", "effective_until": "2027-01-31",
            "knowledge_domain": "national_guidelines", "jurisdiction": "VN",
            "target_population": "Adults",
        }
        self.assertEqual(KnowledgeDocumentCreate(**payload).published_at, "2025-01-15")
    def test_only_unreviewed_or_pending_documents_can_be_reviewed(self):
        self.assertTrue(is_reviewable_status("DISCOVERED"))
        self.assertTrue(is_reviewable_status("AI_REVIEWED"))
        self.assertFalse(is_reviewable_status("CLINICAL_APPROVED"))
        self.assertFalse(is_reviewable_status("REJECTED"))
        self.assertFalse(is_reviewable_status("SUPERSEDED"))
    def test_document_creator_cannot_review_own_document(self):
        self.assertFalse(reviewer_is_independent("user-1", "user-1"))
        self.assertTrue(reviewer_is_independent("user-1", "user-2"))
        self.assertTrue(reviewer_is_independent(None, "user-2"))
    def test_http_url_fails(self):
        metadata = {"title":"Guideline","publisher":"MoH","document_type":"guideline","source_url":"http://moh.gov.vn/doc","published_at":"2025","knowledge_domain":"national_guidelines","jurisdiction":"VN","target_population":"Adults"}
        result = automated_document_checks(metadata)
        self.assertFalse(result["passed"])
        self.assertIn("SOURCE_URL_NOT_HTTPS", result["issues"])

if __name__ == "__main__":
    unittest.main()

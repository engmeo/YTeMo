import unittest
from clinical_knowledge import automated_document_checks, host_is_within, normalize_host

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
        metadata = {"title":"Guideline","publisher":"MoH","document_type":"guideline","source_url":"https://moh.gov.vn/doc","published_at":"2025-01-01"}
        result = automated_document_checks(metadata, "A" * 250)
        self.assertTrue(result["passed"])
        self.assertEqual(result["scope"], "metadata_and_extraction_integrity_only")
        self.assertFalse(result["clinical_approval"])
    def test_http_url_fails(self):
        metadata = {"title":"Guideline","publisher":"MoH","document_type":"guideline","source_url":"http://moh.gov.vn/doc","published_at":"2025"}
        result = automated_document_checks(metadata)
        self.assertFalse(result["passed"])
        self.assertIn("SOURCE_URL_NOT_HTTPS", result["issues"])

if __name__ == "__main__":
    unittest.main()

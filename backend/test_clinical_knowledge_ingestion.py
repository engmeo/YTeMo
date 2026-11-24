import hashlib
import unittest
from io import BytesIO

from reportlab.pdfgen import canvas

from pydantic import ValidationError
from clinical_knowledge_workflows import (
    EvidenceRetrievalRequest, can_access_evidence_scope, retrieve_approved_evidence,
)
from clinical_knowledge_ingestion import (
    IngestionError, _page_quality, discover_pdf_links, extract_pdf_pages,
    is_allowed_source_url, normalize_host,
)



class FakeQuery:
    def __init__(self, rows):
        self.rows = list(rows)
        self.filters = []
        self.max_rows = None

    def select(self, *_args):
        return self

    def eq(self, key, value):
        self.filters.append(("eq", key, value))
        return self

    def in_(self, key, values):
        self.filters.append(("in", key, set(values)))
        return self

    def limit(self, value):
        self.max_rows = value
        return self

    def execute(self):
        rows = self.rows
        for kind, key, value in self.filters:
            if kind == "eq":
                rows = [row for row in rows if row.get(key) == value]
            else:
                rows = [row for row in rows if row.get(key) in value]
        return type("Result", (), {"data": rows[:self.max_rows] if self.max_rows else rows})()


class FakeDB:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return FakeQuery(self.tables.get(name, []))


class ClinicalKnowledgeIngestionTests(unittest.TestCase):
    def test_allowlist_accepts_exact_and_subdomain(self):
        hosts = ["moh.gov.vn"]
        self.assertTrue(is_allowed_source_url("https://moh.gov.vn/file.pdf", hosts))
        self.assertTrue(is_allowed_source_url("https://vanban.moh.gov.vn/file.pdf", hosts))

    def test_allowlist_rejects_offsite_and_unsafe_urls(self):
        hosts = ["moh.gov.vn"]
        for url in (
            "http://moh.gov.vn/file.pdf",
            "https://moh.gov.vn.attacker.example/file.pdf",
            "https://127.0.0.1/file.pdf",
            "https://localhost/file.pdf",
            "https://moh.gov.vn:8443/file.pdf",
            "https://moh.gov.vn:notaport/file.pdf",
            "https://user:pass@moh.gov.vn/file.pdf",
        ):
            with self.subTest(url=url):
                self.assertFalse(is_allowed_source_url(url, hosts))

    def test_discovery_only_keeps_allowlisted_pdf_links(self):
        html = b"""
        <html><body>
          <a href="/docs/guideline.pdf">Official guideline</a>
          <a href="/docs/guideline.pdf">duplicate</a>
          <a href="https://outside.example/file.pdf">offsite</a>
          <a href="/news">news</a>
        </body></html>
        """
        links = discover_pdf_links(html, "https://moh.gov.vn/guidelines", ["moh.gov.vn"])
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["url"], "https://moh.gov.vn/docs/guideline.pdf")

    def test_page_quality_flags_low_confidence_and_low_text(self):
        report = _page_quality("short text", "tesseract_ocr_vie_eng", 42.0)
        self.assertTrue(report["requires_human_check"])
        self.assertIn("LOW_OCR_CONFIDENCE", report["warnings"])

    def test_extract_pdf_preserves_page_numbers_and_hashes(self):
        stream = BytesIO()
        pdf = canvas.Canvas(stream)
        pdf.drawString(72, 720, "Clinical guideline evidence page one")
        pdf.showPage()
        pdf.drawString(72, 720, "Clinical guideline evidence page two")
        pdf.save()
        pages, report = extract_pdf_pages(stream.getvalue(), enable_ocr=False)
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0].page_number, 1)
        self.assertEqual(pages[1].page_number, 2)
        self.assertEqual(pages[0].text_sha256, hashlib.sha256(pages[0].text.encode()).hexdigest())
        self.assertEqual(report["overall_status"], "EXTRACTED")

    def test_evidence_retrieval_requires_controlled_scope_and_population(self):
        payload = {
            "query": "hypertension guideline", "jurisdiction": "VN",
            "population": "Adults", "scope": "patient_education",
        }
        self.assertEqual(EvidenceRetrievalRequest(**payload).jurisdiction, "VN")
        payload["scope"] = "unrestricted"
        with self.assertRaises(ValidationError):
            EvidenceRetrievalRequest(**payload)

    def test_retrieval_excludes_unresolved_conflicts_and_keeps_resolved_context(self):
        claims = [
            {"id":"claim-1","document_id":"doc-1","reviewer_status":"ACCEPTED",
             "claim_text":"Hypertension treatment evidence for adults","exact_quote":"Hypertension treatment is recommended for adults with hypertension.",
             "population":"Adults with hypertension","jurisdiction":"GLOBAL","source_page_number":2,"source_locator":"Page 2"},
            {"id":"claim-2","document_id":"doc-2","reviewer_status":"ACCEPTED",
             "claim_text":"Alternative hypertension treatment evidence for adults","exact_quote":"Alternative hypertension treatment in adults with hypertension.",
             "population":"Adults with hypertension","jurisdiction":"VN","source_page_number":4,"source_locator":"Page 4"},
        ]
        docs = [
            {"id":"doc-1","title":"Guideline A","publisher":"MoH","source_url":"https://moh.gov.vn/a.pdf",
             "version":"1","effective_from":None,"effective_until":None,"knowledge_domain":"who_guidelines",
             "jurisdiction":"GLOBAL","target_population":"Adults","specialty":None,"status":"CLINICAL_APPROVED",
             "is_current":True,"approved_scope":["patient_education"],"original_sha256":"abc"},
            {"id":"doc-2","title":"Guideline B","publisher":"WHO","source_url":"https://who.int/b.pdf",
             "version":"2","effective_from":None,"effective_until":None,"knowledge_domain":"who_guidelines",
             "jurisdiction":"VN","target_population":"Adults","specialty":None,"status":"CLINICAL_APPROVED",
             "is_current":True,"approved_scope":["patient_education"],"original_sha256":"def"},
        ]
        conflicts = [
            {"claim_ids":["claim-2"],"conflict_summary":"Unresolved difference","resolution_status":"OPEN"},
            {"claim_ids":["claim-1"],"conflict_summary":"Resolved difference","resolution_status":"RESOLVED",
             "resolution_rationale":"Two independent reviewers confirmed the contextual interpretation."},
        ]
        db = FakeDB({
            "clinical_evidence_claims": claims,
            "clinical_knowledge_documents": docs,
            "clinical_evidence_conflicts": conflicts,
        })
        request = EvidenceRetrievalRequest(
            query="hypertension treatment", jurisdiction="VN",
            population="Adults with hypertension", scope="patient_education",
        )
        result = retrieve_approved_evidence(db, request)
        self.assertFalse(result["abstention"])
        self.assertEqual([item["claim"]["id"] for item in result["evidence"]], ["claim-1"])
        self.assertEqual(result["evidence"][0]["resolved_conflicts"][0]["summary"], "Resolved difference")

    def test_retrieval_abstains_on_population_mismatch(self):
        db = FakeDB({
            "clinical_evidence_claims": [{"id":"claim-1","document_id":"doc-1","reviewer_status":"ACCEPTED",
                "claim_text":"Hypertension treatment","exact_quote":"Hypertension treatment in adults.",
                "population":"Adults","jurisdiction":"VN","source_page_number":1,"source_locator":"Page 1"}],
            "clinical_knowledge_documents": [{"id":"doc-1","title":"Guideline","publisher":"MoH",
                "source_url":"https://moh.gov.vn/a.pdf","version":"1","effective_from":None,"effective_until":None,
                "knowledge_domain":"national_guidelines","jurisdiction":"VN","target_population":"Adults",
                "specialty":None,"status":"CLINICAL_APPROVED","is_current":True,
                "approved_scope":["patient_education"],"original_sha256":"abc"}],
            "clinical_evidence_conflicts": [],
        })
        request = EvidenceRetrievalRequest(
            query="hypertension treatment", jurisdiction="VN",
            population="Children with hypertension", scope="patient_education",
        )
        result = retrieve_approved_evidence(db, request)
        self.assertTrue(result["abstention"])
        self.assertEqual(result["evidence"], [])
    def test_ingestion_rejects_inverted_effective_dates(self):
        payload = {
            "title": "Guideline", "document_type": "guideline",
            "knowledge_domain": "national_guidelines", "jurisdiction": "VN",
            "target_population": "Adults", "published_at": "2025-01-01",
            "effective_from": "2026-01-01", "effective_until": "2025-01-01",
        }
        with self.assertRaises(ValidationError):
            from clinical_knowledge_workflows import IngestCandidateRequest
            IngestCandidateRequest(**payload)
    def test_high_risk_evidence_scopes_require_verified_professional(self):
        no_reviewer = FakeDB({"clinical_knowledge_reviewers": []})
        user = type("User", (), {"id": "user-1"})()
        self.assertTrue(can_access_evidence_scope(no_reviewer, user, "patient_education"))
        self.assertFalse(can_access_evidence_scope(no_reviewer, user, "treatment_reference"))
        verified = FakeDB({"clinical_knowledge_reviewers": [{
            "user_id": "user-1", "role": "physician", "is_active": True, "credential_verified": True,
            "credential_type": "license", "credential_identifier": "VN-123",
            "credential_verified_at": "2026-01-01T00:00:00Z", "credential_verified_by": "admin-1",
        }]})
        self.assertTrue(can_access_evidence_scope(verified, user, "medication_safety"))
    def test_non_pdf_is_rejected(self):
        with self.assertRaises(IngestionError):
            extract_pdf_pages(b"not a pdf", enable_ocr=False)


if __name__ == "__main__":
    unittest.main()

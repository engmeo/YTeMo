import hashlib
import unittest
from io import BytesIO

from reportlab.pdfgen import canvas

from pydantic import ValidationError
from clinical_knowledge_workflows import EvidenceRetrievalRequest
from clinical_knowledge_ingestion import (
    IngestionError, _page_quality, discover_pdf_links, extract_pdf_pages,
    is_allowed_source_url, normalize_host,
)


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
    def test_non_pdf_is_rejected(self):
        with self.assertRaises(IngestionError):
            extract_pdf_pages(b"not a pdf", enable_ocr=False)


if __name__ == "__main__":
    unittest.main()

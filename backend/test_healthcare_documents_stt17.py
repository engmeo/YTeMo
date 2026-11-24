import pytest

import healthcare_documents as documents


def test_stt17_text_file_extraction_and_no_persistence():
    result = documents.extract_medical_document("record.txt", "Ket qua xet nghiem: Hb 13 g/dL".encode("utf-8"))
    assert result.extraction_status == "text_extracted"
    assert "Hb 13" in result.text
    assert result.persisted is False


def test_stt17_scanned_pdf_uses_ocr_fallback(monkeypatch):
    monkeypatch.setattr(documents, "_extract_pdf", lambda data: ("", 1))
    monkeypatch.setattr(documents, "_ocr_pdf", lambda data: "[Trang 1 - OCR]\nKet qua Hb 13 g/dL")
    result = documents.extract_medical_document("scan.pdf", b"%PDF-test")
    assert result.extraction_status == "ocr_extracted"
    assert "Hb 13" in result.text
    assert result.page_count == 1
    assert result.persisted is False


def test_stt17_scanned_pdf_propagates_ocr_configuration_error(monkeypatch):
    monkeypatch.setattr(documents, "_extract_pdf", lambda data: ("", 1))
    def unavailable(data):
        raise documents.DocumentExtractionError("OCR is not configured")
    monkeypatch.setattr(documents, "_ocr_pdf", unavailable)
    with pytest.raises(documents.DocumentExtractionError, match="OCR is not configured"):
        documents.extract_medical_document("scan.pdf", b"%PDF-test")


def test_stt17_document_size_limit_is_enforced():
    payload = b"x" * (documents.MAX_DOCUMENT_BYTES + 1)
    with pytest.raises(documents.DocumentExtractionError, match="10 MB"):
        documents.extract_medical_document("record.txt", payload)



def test_docling_engine_is_opt_in_and_returns_layout_extraction(monkeypatch):
    import sys
    from types import SimpleNamespace

    monkeypatch.setenv("YTEMO_DOCUMENT_ENGINE", "docling")
    fake = SimpleNamespace(
        text="# Hồ sơ\n| Chỉ số | Kết quả |\n|---|---|\n| HbA1c | 6.2% |",
        page_count=2,
        warnings=(),
    )
    monkeypatch.setitem(
        sys.modules,
        "document_ai_adapter",
        SimpleNamespace(extract_document_with_docling=lambda filename, data: fake),
    )
    result = documents.extract_medical_document("record.pdf", b"%PDF-test")
    assert result.extraction_status == "docling_extracted"
    assert "| HbA1c | 6.2% |" in result.text
    assert result.page_count == 2
    assert result.persisted is False


def test_docling_engine_errors_are_not_silently_hidden(monkeypatch):
    import sys
    from types import SimpleNamespace

    monkeypatch.setenv("YTEMO_DOCUMENT_ENGINE", "docling")
    def fail(filename, data):
        raise RuntimeError("worker unavailable")
    monkeypatch.setitem(
        sys.modules,
        "document_ai_adapter",
        SimpleNamespace(extract_document_with_docling=fail),
    )
    with pytest.raises(documents.DocumentExtractionError, match="worker unavailable"):
        documents.extract_medical_document("record.pdf", b"%PDF-test")

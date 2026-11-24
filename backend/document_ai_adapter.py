"""Optional Docling adapter for layout-aware healthcare document extraction.

This module is intentionally lazy-loaded and is not imported by the API at startup.
Run it in a dedicated document worker: Docling loads ML models and can be CPU/RAM
intensive. It extracts structure; it does not interpret clinical meaning.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any


@dataclass(frozen=True)
class DoclingExtraction:
    text: str
    status: str
    page_count: int | None
    warnings: tuple[str, ...] = ()


def extract_document_with_docling(
    filename: str,
    data: bytes,
    *,
    document_timeout_seconds: int = 90,
) -> DoclingExtraction:
    """Convert PDF/DOCX/TXT/MD bytes to layout-aware Markdown using Docling."""
    if not isinstance(data, bytes) or not data:
        raise ValueError("Document bytes are empty.")
    if len(data) > 10 * 1024 * 1024:
        raise ValueError("Document exceeds the 10 MB processing limit.")

    try:
        from docling.datamodel.base_models import InputFormat, DocumentStream
        from docling.datamodel.pipeline_options import PdfPipelineOptions, TesseractCliOcrOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as exc:
        raise RuntimeError(
            "Docling is not installed. Install backend/requirements-document-ai.txt "
            "in the isolated document-worker environment."
        ) from exc

    # Preserve table structure and OCR for image-only regions. This is deliberately
    # opt-in because first-run model downloads and CPU inference are expensive.
    pdf_options = PdfPipelineOptions(
        do_ocr=True,
        do_table_structure=True,
        ocr_options=TesseractCliOcrOptions(lang=["vie", "eng"]),
        document_timeout=max(15, min(int(document_timeout_seconds), 180)),
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
        }
    )
    stream = DocumentStream(name=filename, stream=BytesIO(data))
    try:
        result = converter.convert(
            stream,
            max_num_pages=100,
            max_file_size=10 * 1024 * 1024,
        )
        document = result.document
        markdown = document.export_to_markdown()
    except Exception as exc:
        raise RuntimeError(
            f"Docling could not process the supplied document ({type(exc).__name__})."
        ) from exc

    if not isinstance(markdown, str) or not markdown.strip():
        raise RuntimeError("Docling completed without extracting readable text.")

    status_value = getattr(result, "status", "unknown")
    status = getattr(status_value, "value", str(status_value))
    pages = getattr(document, "pages", None)
    page_count = len(pages) if pages is not None else None
    errors = getattr(result, "errors", None) or ()
    warnings = tuple(
        str(getattr(item, "error_message", item))[:500]
        for item in errors
    )
    return DoclingExtraction(
        text=markdown.strip()[:200_000],
        status=status,
        page_count=page_count,
        warnings=warnings,
    )

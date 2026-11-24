"""Safe, local-first extraction of text from user-provided healthcare documents.

Files are processed in memory and are not persisted by this module. Supported
formats are text-based PDF, DOCX, TXT and Markdown. Scanned PDFs require an OCR
service and are reported explicitly instead of silently returning empty text.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from typing import Any
import zipfile

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_CHARACTERS = 200_000
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


class DocumentExtractionError(ValueError):
    """Raised when a document cannot be safely or reliably extracted."""


@dataclass(frozen=True)
class DocumentExtraction:
    filename: str
    media_type: str
    extraction_status: str
    text: str
    page_count: int | None
    character_count: int
    truncated: bool
    persisted: bool = False
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1258"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DocumentExtractionError("Không đọc được bảng mã văn bản. Hãy lưu file ở UTF-8.")


def _extract_pdf(data: bytes) -> tuple[str, int]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise DocumentExtractionError("PDF được mã hóa; chưa thể đọc nội dung.")
        pages = []
        for index, page in enumerate(reader.pages):
            page_text = (page.extract_text() or "").strip()
            if page_text:
                pages.append(f"[Trang {index + 1}]\n{page_text}")
        return "\n\n".join(pages), len(reader.pages)
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError("PDF không hợp lệ hoặc không thể trích xuất.") from exc


def _ocr_pdf(data: bytes) -> str:
    """OCR a scanned PDF when optional local OCR dependencies are installed."""
    import os
    import shutil
    tesseract_cmd = os.getenv("TESSERACT_CMD") or shutil.which("tesseract")
    if not tesseract_cmd:
        raise DocumentExtractionError(
            "Chua cau hinh Tesseract OCR. Cai Tesseract va ngon ngu vie+eng, sau do thu lai."
        )
    try:
        import fitz
        import pytesseract
        from PIL import Image
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        languages = pytesseract.get_languages(config="")
        if not {"vie", "eng"}.issubset(set(languages)):
            raise DocumentExtractionError(
                "Tesseract thieu vie.traineddata hoac eng.traineddata."
            )
    except DocumentExtractionError:
        raise
    except ImportError as exc:
        raise DocumentExtractionError(
            "Thieu goi OCR. Cai backend/requirements-ocr.txt trong backend virtualenv."
        ) from exc
    except Exception as exc:
        raise DocumentExtractionError(
            "Khong the khoi dong Tesseract OCR. Kiem tra TESSERACT_CMD va cai dat Tesseract."
        ) from exc
    try:
        pages = []
        with fitz.open(stream=data, filetype="pdf") as pdf:
            for index, page in enumerate(pdf):
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.open(BytesIO(pixmap.tobytes("png")))
                page_text = pytesseract.image_to_string(image, lang="vie+eng").strip()
                if page_text:
                    pages.append(f"[Trang {index + 1} - OCR]\n{page_text}")
                if sum(len(item) for item in pages) >= MAX_EXTRACTED_CHARACTERS:
                    break
        return "\n\n".join(pages)[:MAX_EXTRACTED_CHARACTERS]
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError(
            "OCR that bai. Kiem tra Tesseract, vie.traineddata va file PDF."
        ) from exc


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document
        document = Document(BytesIO(data))
        parts = [p.text.strip() for p in document.paragraphs if p.text.strip()]
        for table_index, table in enumerate(document.tables, start=1):
            parts.append(f"[Bảng {table_index}]")
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " / ") for cell in row.cells]
                if any(cells):
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    except Exception as exc:
        raise DocumentExtractionError("DOCX không hợp lệ hoặc không thể trích xuất.") from exc


def extract_medical_document(filename: str, data: bytes) -> DocumentExtraction:
    """Extract text from a supported document without storing the uploaded bytes."""
    safe_name = Path((filename or "document").replace("\\", "/")).name
    extension = Path(safe_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentExtractionError("Chỉ hỗ trợ PDF, DOCX, TXT và Markdown.")
    if not isinstance(data, bytes) or not data:
        raise DocumentExtractionError("File rỗng hoặc không hợp lệ.")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise DocumentExtractionError("File vượt giới hạn 10 MB.")

    # Optional layout-aware extraction. Keep the lightweight parser as the
    # default for API latency and small-memory deployments; Docling belongs in
    # an isolated worker and is enabled explicitly per deployment.
    import os
    if os.getenv("YTEMO_DOCUMENT_ENGINE", "builtin").strip().lower() == "docling":
        if extension not in {".pdf", ".docx", ".txt", ".md"}:
            raise DocumentExtractionError("Docling không hỗ trợ định dạng file này.")
        try:
            from document_ai_adapter import extract_document_with_docling
            parsed = extract_document_with_docling(safe_name, data)
        except Exception as exc:
            raise DocumentExtractionError(
                f"Docling không thể xử lý hồ sơ: {type(exc).__name__}: {str(exc)[:300]}"
            ) from exc
        parsed_text = parsed.text[:MAX_EXTRACTED_CHARACTERS]
        truncated = len(parsed.text) > MAX_EXTRACTED_CHARACTERS
        media_types = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".md": "text/markdown",
        }
        return DocumentExtraction(
            filename=safe_name,
            media_type=media_types[extension],
            extraction_status="docling_extracted",
            text=parsed_text,
            page_count=parsed.page_count,
            character_count=len(parsed_text),
            truncated=truncated,
            persisted=False,
            limitations=(
                "Docling trích xuất bố cục/bảng biểu; không xác thực nội dung y khoa.",
                "OCR có thể sai; phải đối chiếu với ảnh/trang hồ sơ gốc.",
                "Kết quả không tự động trở thành dữ liệu huấn luyện hoặc clinical evidence đã duyệt.",
                *parsed.warnings[:5],
            ),
        )

    page_count = None
    ocr_used = False
    if extension == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise DocumentExtractionError("Nội dung file không khớp định dạng PDF.")
        text, page_count = _extract_pdf(data)
        if not text.strip():
            text = _ocr_pdf(data)
            ocr_used = bool(text.strip())
        media_type = "application/pdf"
    elif extension == ".docx":
        if not data.startswith(b"PK"):
            raise DocumentExtractionError("Nội dung file không khớp định dạng DOCX.")
        try:
            with zipfile.ZipFile(BytesIO(data)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise DocumentExtractionError("File ZIP không phải tài liệu DOCX.")
        except zipfile.BadZipFile as exc:
            raise DocumentExtractionError("DOCX không hợp lệ.") from exc
        text = _extract_docx(data)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        if b"\x00" in data[:4096]:
            raise DocumentExtractionError("File văn bản chứa dữ liệu nhị phân không hợp lệ.")
        text = _decode_text(data)
        media_type = "text/markdown" if extension == ".md" else "text/plain"

    text = "\n".join(line.rstrip() for line in text.replace("\x00", "").splitlines()).strip()
    if not text:
        if extension == ".pdf":
            raise DocumentExtractionError(
                "PDF không có lớp văn bản (có thể là bản scan). Cần OCR trước khi phân tích."
            )
        raise DocumentExtractionError("Không tìm thấy nội dung văn bản trong file.")

    truncated = len(text) > MAX_EXTRACTED_CHARACTERS
    if truncated:
        text = text[:MAX_EXTRACTED_CHARACTERS]
    return DocumentExtraction(
        filename=safe_name,
        media_type=media_type,
        extraction_status="ocr_extracted" if ocr_used else "text_extracted",
        text=text,
        page_count=page_count,
        character_count=len(text),
        truncated=truncated,
        persisted=False,
        limitations=(
            "Chỉ trích xuất văn bản; không xác thực tính đúng/sai của hồ sơ.",
            "OCR fallback is available for scanned PDFs when local dependencies are configured.",
            "File được xử lý trong bộ nhớ của request và không được lưu bởi endpoint này.",
        ),
    )

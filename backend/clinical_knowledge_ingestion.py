"""Controlled ingestion and page-level extraction for official clinical sources.

This module does not determine clinical correctness. It fetches only HTTPS URLs
on explicitly registered publisher domains, preserves original bytes, and
records page-level extraction diagnostics for human quality review.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urlunparse

import requests

MAX_SOURCE_BYTES = 25 * 1024 * 1024
MAX_HTML_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 300
MAX_TOTAL_TEXT = 2_000_000
REQUEST_TIMEOUT = (5, 20)
USER_AGENT = "YTeMo-ClinicalKnowledgeBot/1.0 (+https://github.com/engmeo/YTeMo)"


class IngestionError(ValueError):
    pass


def normalize_host(url: str) -> str:
    return (urlparse(url).hostname or "").lower().rstrip(".").removeprefix("www.")


def is_allowed_source_url(url: str, registered_hosts: list[str]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    if port not in (None, 443):
        return False
    host = parsed.hostname.lower().rstrip(".")
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return False
    return any(host == base or host.endswith("." + base) for base in registered_hosts)


def _assert_public_resolution(host: str) -> None:
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise IngestionError("Không phân giải được tên miền nguồn.") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise IngestionError("Tên miền nguồn phân giải tới địa chỉ mạng nội bộ; đã chặn để tránh SSRF.")


def fetch_registered_url(url: str, registered_hosts: list[str], max_bytes: int = MAX_SOURCE_BYTES) -> tuple[bytes, str, str]:
    current = url
    for _ in range(5):
        if not is_allowed_source_url(current, registered_hosts):
            raise IngestionError("URL không thuộc HTTPS domain đã đăng ký hoặc có cấu hình không an toàn.")
        host = urlparse(current).hostname or ""
        _assert_public_resolution(host)
        try:
            session = requests.Session()
            session.trust_env = False
            response = session.get(
                current, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.1"},
                timeout=REQUEST_TIMEOUT, stream=True, allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise IngestionError("Không thể tải tài liệu từ nguồn đã đăng ký.") from exc
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise IngestionError("Nguồn trả về redirect không có Location.")
            current = urljoin(current, location)
            continue
        if response.status_code != 200:
            status = response.status_code
            response.close()
            raise IngestionError(f"Nguồn trả về HTTP {status}; chỉ chấp nhận HTTP 200.")
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                declared_size = int(content_length)
            except ValueError:
                response.close()
                raise IngestionError("Nguồn trả về Content-Length không hợp lệ.")
            if declared_size > max_bytes:
                response.close()
                raise IngestionError("Tài liệu vượt giới hạn dung lượng cho phép.")
        chunks, total = [], 0
        try:
            for chunk in response.iter_content(1024 * 128):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise IngestionError("Tài liệu vượt giới hạn dung lượng cho phép.")
                chunks.append(chunk)
        except requests.RequestException as exc:
            raise IngestionError("Kết nối bị gián đoạn khi tải tài liệu.") from exc
        finally:
            response.close()
            session.close()
        data = b"".join(chunks)
        return data, response.headers.get("Content-Type", "").split(";")[0].lower(), response.url
    raise IngestionError("Nguồn chuyển hướng quá nhiều lần.")


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data.strip())

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.links.append({"href": self._href, "text": " ".join(x for x in self._text if x)})
            self._href, self._text = None, []


def discover_pdf_links(html: bytes, page_url: str, registered_hosts: list[str]) -> list[dict[str, str]]:
    parser = LinkCollector()
    try:
        parser.feed(html.decode("utf-8", errors="replace"))
    except Exception as exc:
        raise IngestionError("Không phân tích được trang danh mục nguồn.") from exc
    found, seen = [], set()
    for link in parser.links:
        href = (link.get("href") or "").strip()
        if not href:
            continue
        candidate = urljoin(page_url, href).split("#", 1)[0]
        parsed = urlparse(candidate)
        if parsed.path.lower().endswith(".pdf") and is_allowed_source_url(candidate, registered_hosts):
            canonical = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))
            if canonical not in seen:
                seen.add(canonical)
                found.append({"url": canonical, "link_text": link.get("text", "")[:500]})
    return found[:200]


def _page_quality(text: str, extraction_method: str, ocr_confidence: float | None = None) -> dict:
    stripped = text.strip()
    replacement = stripped.count("\ufffd")
    alnum = sum(ch.isalnum() for ch in stripped)
    ratio = alnum / max(1, len(stripped))
    warnings = []
    if len(stripped) < 40:
        warnings.append("LOW_TEXT_VOLUME")
    if replacement:
        warnings.append("REPLACEMENT_CHARACTERS")
    if ratio < 0.25 and len(stripped) > 80:
        warnings.append("LOW_ALPHANUMERIC_RATIO")
    if ocr_confidence is not None and ocr_confidence < 65:
        warnings.append("LOW_OCR_CONFIDENCE")
    return {
        "text_characters": len(stripped), "alphanumeric_ratio": round(ratio, 4),
        "replacement_characters": replacement, "ocr_mean_confidence": ocr_confidence,
        "extraction_method": extraction_method, "warnings": warnings,
        "requires_human_check": bool(warnings),
        "note": "Heuristic extraction-quality indicators only; not a clinical accuracy score.",
    }


@dataclass
class ExtractedPage:
    page_number: int
    text: str
    text_sha256: str
    quality: dict
    extraction_status: str


def extract_pdf_pages(data: bytes, enable_ocr: bool = True) -> tuple[list[ExtractedPage], dict]:
    if not data.startswith(b"%PDF-"):
        raise IngestionError("Nội dung tải về không phải PDF hợp lệ.")
    try:
        from pypdf import PdfReader
        from io import BytesIO
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise IngestionError("PDF được mã hóa; không thể xử lý tự động.")
        if len(reader.pages) == 0 or len(reader.pages) > MAX_PDF_PAGES:
            raise IngestionError(f"PDF phải có từ 1 đến {MAX_PDF_PAGES} trang.")
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError("Không đọc được cấu trúc PDF.") from exc

    pages: list[ExtractedPage] = []
    ocr_engine = None
    ocr_pdf = None
    ocr_error = None
    total_chars = 0
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            text = ""
        method = "pdf_text"
        confidence = None
        if enable_ocr and len(text) < 40:
            try:
                if ocr_engine is None:
                    import fitz
                    import pytesseract
                    from PIL import Image
                    ocr_pdf = fitz.open(stream=data, filetype="pdf")
                    ocr_engine = (fitz, pytesseract, Image)
                fitz, pytesseract, Image = ocr_engine
                ocr_page = ocr_pdf[index - 1]
                page_area = float(ocr_page.rect.width) * float(ocr_page.rect.height)
                if page_area <= 0 or page_area > 100_000_000:
                    raise IngestionError("Kích thước trang vượt giới hạn OCR an toàn.")
                scale = min(1.8, (35_000_000 / page_area) ** 0.5)
                pix = ocr_page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                with Image.open(BytesIO(pix.tobytes("png"))) as image:
                    ocr_data = pytesseract.image_to_data(
                        image, lang="vie+eng", output_type=pytesseract.Output.DICT
                    )
                words, confidences = [], []
                for word, raw_conf in zip(ocr_data.get("text", []), ocr_data.get("conf", [])):
                    word = str(word).strip()
                    try:
                        conf = float(raw_conf)
                    except (TypeError, ValueError):
                        conf = -1
                    if word:
                        words.append(word)
                    if conf >= 0:
                        confidences.append(conf)
                if words:
                    text = " ".join(words)
                    confidence = sum(confidences) / len(confidences) if confidences else None
                    method = "tesseract_ocr_vie_eng"
            except Exception as exc:
                ocr_error = type(exc).__name__
        total_chars += len(text)
        if total_chars > MAX_TOTAL_TEXT:
            if ocr_pdf is not None:
                ocr_pdf.close()
            raise IngestionError("Tổng nội dung trích xuất vượt giới hạn an toàn.")
        quality = _page_quality(text, method, confidence)
        status = "EXTRACTED" if text else ("OCR_UNAVAILABLE" if ocr_error else "EMPTY")
        pages.append(ExtractedPage(
            page_number=index, text=text,
            text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            quality=quality, extraction_status=status,
        ))
    if ocr_pdf is not None:
        ocr_pdf.close()
    report = {
        "page_count": len(pages), "extracted_pages": sum(bool(p.text.strip()) for p in pages),
        "pages_needing_human_check": [p.page_number for p in pages if p.quality["requires_human_check"]],
        "empty_pages": [p.page_number for p in pages if not p.text.strip()],
        "ocr_error": ocr_error, "total_characters": total_chars,
        "overall_status": "EXTRACTED" if all(p.text.strip() for p in pages) else "PARTIAL",
        "quality_note": "Page-level heuristics do not certify OCR correctness or clinical content.",
    }
    return pages, report

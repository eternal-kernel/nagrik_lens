"""PDF inspection and diagnostic service.

Validates that an uploaded file is a well-formed PDF (size, magic bytes, structure),
computes its SHA-256 integrity hash, and produces per-page diagnostics
(embedded text vs. scanned image requiring OCR fallback).
"""

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import shutil
from typing import Any, Dict, List
import pymupdf

MAX_PDF_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
MIN_CHARS_FOR_EMBEDDED_TEXT = 40


def is_ocr_available() -> bool:
    """Check if the system has tesseract OCR binary installed."""
    return shutil.which("tesseract") is not None


@dataclass
class PageDiagnostic:
    page_number: int
    char_count: int
    has_embedded_text: bool
    extraction_method: str  # "embedded_text" | "ocr_fallback" | "ocr_unavailable"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InspectionReport:
    file_hash: str
    file_size_bytes: int
    page_count: int
    digital_pages: int
    scanned_pages: int
    ocr_available: bool
    page_diagnostics: List[PageDiagnostic]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_hash": self.file_hash,
            "file_size_bytes": self.file_size_bytes,
            "page_count": self.page_count,
            "digital_pages": self.digital_pages,
            "scanned_pages": self.scanned_pages,
            "ocr_available": self.ocr_available,
            "page_diagnostics": [p.to_dict() for p in self.page_diagnostics],
        }


def validate_pdf_bytes(pdf_bytes: bytes) -> None:
    """Validate raw bytes belong to a valid PDF within size limits."""
    if not pdf_bytes:
        raise ValueError("Invalid PDF file: File is empty.")

    if len(pdf_bytes) > MAX_PDF_SIZE_BYTES:
        raise ValueError(
            f"File size exceeds 25 MB limit ({len(pdf_bytes)} bytes > {MAX_PDF_SIZE_BYTES} bytes)."
        )

    # Magic byte check
    if not pdf_bytes.startswith(b"%PDF"):
        # Check within the first 1024 bytes in case of leading whitespace or BOM
        if b"%PDF" not in pdf_bytes[:1024]:
            raise ValueError("Invalid PDF file: Missing '%PDF' header signature.")


def inspect_pdf_document(doc: pymupdf.Document, pdf_bytes: bytes) -> InspectionReport:
    """Produce detailed diagnostics for an open PyMuPDF document."""
    hasher = hashlib.sha256(pdf_bytes)
    file_hash = hasher.hexdigest()
    file_size_bytes = len(pdf_bytes)
    page_count = len(doc)

    if page_count == 0:
        raise ValueError("Invalid PDF file: Document contains 0 pages.")

    ocr_ready = is_ocr_available()
    page_diagnostics: List[PageDiagnostic] = []
    digital_pages = 0
    scanned_pages = 0

    for idx, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        char_count = len(text)
        has_embedded = char_count >= MIN_CHARS_FOR_EMBEDDED_TEXT

        if has_embedded:
            digital_pages += 1
            method = "embedded_text"
        else:
            scanned_pages += 1
            method = "ocr_fallback" if ocr_ready else "ocr_unavailable"

        page_diagnostics.append(
            PageDiagnostic(
                page_number=idx,
                char_count=char_count,
                has_embedded_text=has_embedded,
                extraction_method=method,
            )
        )

    return InspectionReport(
        file_hash=file_hash,
        file_size_bytes=file_size_bytes,
        page_count=page_count,
        digital_pages=digital_pages,
        scanned_pages=scanned_pages,
        ocr_available=ocr_ready,
        page_diagnostics=page_diagnostics,
    )


def inspect_pdf(pdf_path: Path | str) -> InspectionReport:
    """Inspect a PDF file from disk."""
    path = Path(pdf_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"PDF file not found at: {path}")

    with open(path, "rb") as f:
        pdf_bytes = f.read()

    validate_pdf_bytes(pdf_bytes)

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Corrupt or unreadable PDF document: {e}")

    try:
        return inspect_pdf_document(doc, pdf_bytes)
    finally:
        doc.close()


def inspect_pdf_content(pdf_bytes: bytes) -> InspectionReport:
    """Inspect PDF directly from raw bytes in memory."""
    validate_pdf_bytes(pdf_bytes)

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Corrupt or unreadable PDF document: {e}")

    try:
        return inspect_pdf_document(doc, pdf_bytes)
    finally:
        doc.close()

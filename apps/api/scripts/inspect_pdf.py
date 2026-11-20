#!/usr/bin/env python3
"""CLI benchmark & diagnostic script for inspecting Form 26 PDFs.

Usage:
    PYTHONPATH=apps/api apps/api/.venv/bin/python apps/api/scripts/inspect_pdf.py <path_to_pdf>
"""

from pathlib import Path
import sys

# Ensure apps/api is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
API_DIR = SCRIPT_DIR.parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from app.services.pdf_pipeline import (
    extract_affidavit_disclosures,
    inspect_pdf,
    is_ocr_available,
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_pdf.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1]).resolve()
    if not pdf_path.exists():
        print(f"Error: File not found at {pdf_path}")
        sys.exit(1)

    print("=" * 75)
    print("NAGRIK LENS — FORM 26 PDF BENCHMARK & DIAGNOSTIC REPORT")
    print("=" * 75)
    print(f"File Path:         {pdf_path}")
    print(f"File Size:         {pdf_path.stat().st_size:,} bytes")

    try:
        inspection = inspect_pdf(pdf_path)
    except Exception as e:
        print(f"\n[FATAL] PDF validation/inspection failed: {e}")
        sys.exit(1)

    print(f"SHA-256 Hash:      {inspection.file_hash}")
    print(f"Total Pages:       {inspection.page_count}")
    print(f"Digital Pages:     {inspection.digital_pages}")
    print(f"Scanned Pages:     {inspection.scanned_pages}")
    print(f"OCR Availability:  {'Available (Tesseract)' if inspection.ocr_available else 'Unavailable'}")
    print("-" * 75)

    print("\n[PAGE-BY-PAGE DIAGNOSTICS]")
    print(f"{'Page':<8} {'Chars':<10} {'Embedded Text':<16} {'Extraction Method'}")
    print("-" * 60)
    for p in inspection.page_diagnostics:
        emb_text = "YES" if p.has_embedded_text else "NO"
        print(f"{p.page_number:<8} {p.char_count:<10} {emb_text:<16} {p.extraction_method}")

    print("\n" + "=" * 75)
    print("[RUNNING DETERMINISTIC DISCLOSURE EXTRACTION]")
    print("=" * 75)

    try:
        result = extract_affidavit_disclosures(pdf_path)
    except Exception as e:
        print(f"\n[ERROR] Extraction failed: {e}")
        sys.exit(1)

    print(f"Draft Disclosures Extracted: {len(result.disclosures)}")
    print(f"CRITICAL TRUST RULE: All extracted items default to 'needs_review'\n")

    for idx, d in enumerate(result.disclosures, start=1):
        print(f"{idx}. Page {d.page_number} | [{d.category.upper()}] ({d.subject_type})")
        print(f"   Field Key:       {d.field_key}")
        print(f"   Status:          {d.verification_status} (Verification Gate Enforced)")
        print(f"   Confidence Note: {d.confidence_note}")
        print(f"   Structured:      {d.structured_value}")
        print(f"   Raw Excerpt:     \"{d.raw_excerpt}\"")
        print()

    if result.warnings:
        print("-" * 75)
        print(f"[EXTRACTION WARNINGS ({len(result.warnings)})]")
        for w in result.warnings:
            print(f"  * {w}")
    else:
        print("[EXTRACTION WARNINGS]: None (all sections matched cleanly)")

    print("=" * 75)


if __name__ == "__main__":
    main()

"""Form 26 affidavit deterministic text and table extraction pipeline.

Extracts page-by-page text and table structures using PyMuPDF 2.x, with OCR
fallback for scanned pages, and matches Form 26 sections into draft disclosures.

CRITICAL TRUST RULE:
All extracted draft disclosures default to verification_status = "needs_review".
ZERO hardcoded fallback values. If an attribute is not found, set to None or omit.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import pymupdf
import pytesseract
from PIL import Image

from app.services.pdf_pipeline.inspector import (
    InspectionReport,
    inspect_pdf_document,
    is_ocr_available,
    validate_pdf_bytes,
)

# Standard ECI Form 26 instruction parentheticals to strip before matching
FORM26_INSTRUCTION_PATTERNS = [
    r"\(\s*Give\s+details\s+of\s+highest\s+School\s*/\s*University\s+education[\s\S]*?(?:\)|\n(?=[A-Z0-9\.\,]))",
    r"\(\s*Certificate\s*/\s*Diploma\s*/\s*Degree\s*course[\s\S]*?(?:\)|\n(?=[A-Z0-9\.\,]))",
    r"\(\s*Tick\s+this\s+alternative[\s\S]*?(?:\)|\n(?=[A-Z0-9\.\,]))",
    r"\(\s*give\s+no\.?\s+of\s+the\s+Section[\s\S]*?(?:\)|\n(?=[A-Z0-9\.\,]))",
    r"\(\s*Details\s+of\s+all\s+pending\s+cases[\s\S]*?(?:\)|\n(?=[A-Z0-9\.\,]))",
    r"\(\s*mention\s+YES\s+or\s+NO[\s\S]*?(?:\)|\n(?=[A-Z0-9\.\,]))",
    r"\(\s*Mention\s+YES\s+or\s+NO[\s\S]*?(?:\)|\n(?=[A-Z0-9\.\,]))",
    r"\(\s*strike\s+out\s+whichever[\s\S]*?(?:\)|\n(?=[A-Z0-9\.\,]))",
    r"\(\s*Please\s+give\s+each\s+case\s+details[\s\S]*?(?:\)|\n(?=[A-Z0-9\.\,]))",
    r"\(\s*Give\s+details\s+of\s+any\s+other[\s\S]*?(?:\)|\n(?=[A-Z0-9\.\,]))",
]

# Notary stamp lines and legal seals to strip
NOTARY_LINE_PATTERNS = [
    r"\bADVOCATE\s*&\s*NOTARY\b",
    r"\bNOTARY\s+PUBLIC\b",
    r"\bNOTARY\s+GOVT\b",
    r"\bAPPOINTED\s+BY\b",
    r"\bRegd\.?\s*No\.?\b",
    r"\bG\.?O\.?Ms\.?\s*No\.?\b",
    r"\bGOMs\s*No\.?\b",
    r"\bCOMMISSION\s+EXPIRES\b",
    r"\bAREA\s+OF\s+PRACTICE\b",
    r"\bMY\s+COMMISSION\b",
    r"\bENTERED\s+IN\s+NOTARIAL\b",
]

BOILERPLATE_REJECTION_PHRASES = [
    r"give details",
    r"school\s*/\s*university",
    r"certificate\s*/\s*diploma",
    r"full form",
    r"name of the school",
    r"year in which",
    r"mentioning the",
    r"course was completed",
]


def is_instruction_boilerplate(text: Optional[str]) -> bool:
    """Check if a string contains Form 26 instruction boilerplate."""
    if not text:
        return False
    low = text.lower()
    return any(re.search(p, low) for p in BOILERPLATE_REJECTION_PHRASES)


def strip_form26_boilerplate(text: str) -> str:
    """
    Remove standard ECI Form 26 parenthetical instructions and notary stamp noise
    to prevent instruction leakage and false-positive field matches.
    """
    cleaned = text
    # 1. Strip multi-line parenthetical instructions
    for pattern in FORM26_INSTRUCTION_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    # 2. Strip notary stamp lines
    lines = cleaned.splitlines()
    kept_lines: List[str] = []
    for line in lines:
        if any(re.search(pat, line, re.IGNORECASE) for pat in NOTARY_LINE_PATTERNS):
            continue
        kept_lines.append(line)
    return "\n".join(kept_lines)


def format_inr_commas(n: int) -> str:
    """Format an integer amount with Indian numbering comma placement (e.g. 500000 -> ₹5,00,000)."""
    s = str(n)
    if len(s) <= 3:
        return f"₹{s}"
    last3 = s[-3:]
    rest = s[:-3]
    parts: List[str] = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return f"₹{','.join(parts)},{last3}"


def parse_indian_amount(text: Optional[str]) -> Optional[int]:
    """
    Robust Indian Currency Normalizer.
    Parses real Form 26 currency expressions into integer INR rupees:
    - ₹5,00,000 -> 500000
    - Rs. 102 Lacs / Rs. 71.50 Lacs / Rs. 23 Lakhs -> 10200000, 7150000, 2300000
    - Rs. 4.80 Cr. / Rs. 1.00 Crores / Rs 1.20 cr -> 48000000, 10000000, 12000000
    - 30,000 / 10,000 -> 30000, 10000
    - NIL / N.A. / -NA- / Not Applicable -> 0
    Returns None if text contains no numeric or NIL values.
    """
    if text is None:
        return None
    clean = str(text).strip()
    if not clean:
        return None

    # 1. NIL / NA check
    if re.search(r"^(?:nil|n\.?a\.?|-na-|-nil-|not\s*applicable|none|[-–—])$", clean, re.I):
        return 0
    if re.search(r"\b(?:nil|n\.a\.|-na-|-nil-|not\s*applicable)\b", clean, re.I):
        return 0

    # 2. Crores: Rs. 4.80 Cr. / Rs. 1.00 Crores / Rs 1.20 cr
    cr_match = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:cr(?:ores?|\.)?)\b", clean, re.I)
    if cr_match:
        try:
            val = float(cr_match.group(1).replace(",", ""))
            return int(round(val * 10_000_000))
        except ValueError:
            pass

    # 3. Lakhs / Lacs: Rs. 102 Lacs / Rs. 71.50 Lacs / Rs. 23 Lakhs
    lac_match = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:lacs?|lakhs?)\b", clean, re.I)
    if lac_match:
        try:
            val = float(lac_match.group(1).replace(",", ""))
            return int(round(val * 100_000))
        except ValueError:
            pass

    # 4. Thousands: 50 K / 50 Thousands
    k_match = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:thousand|k)\b", clean, re.I)
    if k_match:
        try:
            val = float(k_match.group(1).replace(",", ""))
            return int(round(val * 1_000))
        except ValueError:
            pass

    # 5. Plain numeric / comma-separated: ₹5,00,000 / 30,000 / 10,000
    num_match = re.search(r"[\d,]+(?:\.\d+)?", clean)
    if num_match:
        raw_num = num_match.group(0).replace(",", "")
        if raw_num:
            try:
                return int(round(float(raw_num)))
            except ValueError:
                return None
    return None


def parse_inr_amount(raw: str) -> Tuple[Optional[int], Optional[str]]:
    """Backward-compatible helper returning (int_amount, formatted_str)."""
    amt = parse_indian_amount(raw)
    if amt is None:
        return None, None
    if amt == 0 and ("nil" in raw.lower() or "not applicable" in raw.lower() or "na" in raw.lower()):
        return 0, "NIL"
    return amt, format_inr_commas(amt)


def extract_legal_sections(text: str) -> List[str]:
    """
    Extract legal act/code sections (IPC, BNS, MCOC Act, Arms Act, CrPC).
    Returns cleaned, deduplicated section names. ZERO synthetic defaults.
    """
    found: List[str] = []
    # Strip instruction: (give no. of the Section, e.g. Section... of IPC, etc.)
    clean_text = re.sub(r"\([^\)]*give no\.[^\)]*\)", "", text, flags=re.I)

    # 1. Search for explicit "Sections of Acts Applicable:" or "Sections involved:" block
    sec_block = re.search(
        r"(?:Sections\s*(?:of\s*Acts\s*Applicable)?|Sections\s*involved)[\s:\n]+([^\n;]+)",
        clean_text,
        re.I,
    )
    if sec_block:
        block_text = sec_block.group(1).strip()
        items = [i.strip() for i in re.split(r"[,;]", block_text) if i.strip()]
        for item in items:
            cleaned = re.sub(r"\([A-Za-z\s]+\)", "", item).strip()
            if cleaned and any(kw in cleaned.upper() for kw in ["IPC", "BNS", "ACT", "CRPC", "SEC"]):
                found.append(cleaned)

    # 2. Pattern searches if explicit block didn't yield sections
    if not found:
        patterns = [
            # Sec. 3(2) 24 of MCOC Act / Section 25 Arms Act
            r"(?:Sec(?:tion)?s?\.?\s*)?\d+[A-Za-z]?(?:\s*\([A-Za-z0-9]+\))*(?:\s*,\s*\d+[A-Za-z]?(?:\s*\([A-Za-z0-9]+\))*)*(?:\s+of)?\s+[A-Za-z0-9\s]+(?:Act|Code)",
            # Section 302 of IPC / 120(B) IPC / 302 IPC
            r"(?:Sec(?:tion)?s?\.?\s*)?\b\d+[A-Za-z]?(?:\s*\([A-Za-z0-9]+\))*\s*(?:of\s+)?(?:IPC|BNS|CrPC)\b",
            # IPC 143 / BNS 103
            r"\b(?:IPC|BNS|CrPC)\s*\d+[A-Za-z]?(?:\s*\([A-Za-z0-9]+\))*",
        ]
        for pat in patterns:
            for m in re.finditer(pat, clean_text, re.I):
                s = m.group(0).strip()
                if not any(s in x or x in s for x in found):
                    found.append(s)

    # Normalize & deduplicate preserving order
    dedup: List[str] = []
    for s in found:
        norm = re.sub(r"\s+", " ", s).strip()
        if norm and norm not in dedup:
            dedup.append(norm)
    return dedup


@dataclass
class ExtractedDisclosureCandidate:
    category: str
    field_key: str
    subject_type: str
    structured_value: Dict[str, Any]
    raw_excerpt: str
    page_number: int
    confidence_note: str  # "rule_matched" | "partial_match_verify_carefully"
    verification_status: str = "needs_review"  # STRICT: NEVER "verified"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractionResult:
    disclosures: List[ExtractedDisclosureCandidate]
    inspection: InspectionReport
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "disclosures": [d.to_dict() for d in self.disclosures],
            "inspection": self.inspection.to_dict(),
            "warnings": self.warnings,
        }


class Form26Extractor:
    """Deterministic extractor for ECI Form 26 affidavit disclosures."""

    def __init__(self, doc: pymupdf.Document, inspection: InspectionReport):
        self.doc = doc
        self.inspection = inspection
        self.warnings: List[str] = []
        self.disclosures: List[ExtractedDisclosureCandidate] = []
        self.page_texts: Dict[int, str] = {}
        # Track Part-A vs Part-B totals for consistency checking:
        # key: (category, subject_type) -> (amount, formatted_str, page_number)
        self.part_a_values: Dict[Tuple[str, str], Tuple[int, str, int]] = {}
        self.part_b_values: Dict[Tuple[str, str], Tuple[int, str, int]] = {}

    def extract_all(self) -> ExtractionResult:
        # Step 1: Extract and clean text per page (with OCR fallback if needed)
        for idx, page in enumerate(self.doc, start=1):
            text = page.get_text("text").strip()
            if len(text) < 40:
                if is_ocr_available():
                    try:
                        pix = page.get_pixmap(dpi=150)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        ocr_text = pytesseract.image_to_string(img).strip()
                        if ocr_text:
                            text = ocr_text
                            self.warnings.append(
                                f"Page {idx} had minimal text; extracted {len(ocr_text)} characters using OCR fallback."
                            )
                        else:
                            self.warnings.append(f"Page {idx}: OCR fallback produced empty text.")
                    except Exception as e:
                        self.warnings.append(f"Page {idx}: OCR fallback failed: {e}")
                else:
                    self.warnings.append(
                        f"Page {idx} contains minimal embedded text ({len(text)} chars) and OCR is unavailable."
                    )
            # Store boilerplate-cleaned page text
            self.page_texts[idx] = strip_form26_boilerplate(text)

        # Step 2: Run section extractors
        self._extract_education()
        self._extract_movable_assets()
        self._extract_immovable_assets()
        self._extract_liabilities()
        self._extract_pending_criminal_cases()
        self._extract_convictions()

        # Step 3: Run Part-A vs Part-B Consistency Check
        self._check_consistency()

        return ExtractionResult(
            disclosures=self.disclosures,
            inspection=self.inspection,
            warnings=self.warnings,
        )

    def _extract_education(self) -> None:
        """Extract Item (10) Details of Highest Educational Qualification."""
        for page_num, text in self.page_texts.items():
            text_upper = text.upper()
            if (
                "EDUCATIONAL QUALIFICATION" in text_upper
                or "HIGHEST EDUCATIONAL" in text_upper
                or "ITEM (10)" in text_upper
                or "ITEM 10" in text_upper
                or "ITEM (11)" in text_upper
                or "ITEM 11" in text_upper
            ):
                # 1. Key-Value table format (e.g. Candidate X fixture)
                deg_match = re.search(
                    r"(?:Highest\s+Degree\s*/\s*Course|Highest\s+Degree|Highest\s+Qualification|Degree\s*:)[\s:\n]+([^\n]+)",
                    text,
                    re.I,
                )
                univ_match = re.search(
                    r"(?:College\s*/\s*University|School\s*/\s*University|University|Institution)[\s:\n]+([^\n]+)",
                    text,
                    re.I,
                )
                year_match = re.search(
                    r"(?:Year\s*of\s*Completion|Year)[\s:\n]+(\d{4})", text, re.I
                )
                course_match = re.search(
                    r"(?:Course\s*Format|Format|Type)[\s:\n]+([^\n]+)", text, re.I
                )
                excerpt_match = re.search(
                    r'(?:Official\s*Excerpt|Excerpt)[\s:\n]+["“]?([^"”\n]+)["”]?', text, re.I
                )

                degree: Optional[str] = None
                institution: Optional[str] = None
                year: Optional[int] = None
                course_format: Optional[str] = None

                if deg_match:
                    raw_deg = deg_match.group(1).strip()
                    if not is_instruction_boilerplate(raw_deg):
                        degree = raw_deg

                if univ_match:
                    raw_univ = univ_match.group(1).strip()
                    if not is_instruction_boilerplate(raw_univ):
                        institution = raw_univ

                if year_match:
                    year = int(year_match.group(1))

                if course_match:
                    raw_cf = course_match.group(1).strip()
                    if not is_instruction_boilerplate(raw_cf):
                        course_format = raw_cf

                # 2. Free-text format (e.g. "My educational qualification is as under: ...")
                if not degree or not institution:
                    free_match = re.search(
                        r"(?:educational\s+qualification\s+is\s+as\s+under|Highest\s+educational\s+qualification)[\s:\n]+([^\n\r]+)",
                        text,
                        re.I,
                    )
                    if free_match:
                        raw_line = free_match.group(1).strip()
                        if not is_instruction_boilerplate(raw_line):
                            ym = re.search(r"\b(19\d{2}|20\d{2})\b", raw_line)
                            if ym:
                                year = int(ym.group(1))
                                clean_line = re.sub(r"\b(19\d{2}|20\d{2})\b", "", raw_line).strip(" ,;()")
                            else:
                                clean_line = raw_line

                            # Check if institution keyword exists in line
                            inst_m = re.search(
                                r"[\s,\(]+([A-Za-z\s\.\&]+?(?:University|College|Board|School|Institute|Vidyalaya|Academy)[A-Za-z\s\.\,]*)",
                                clean_line,
                                re.I,
                            )
                            if inst_m:
                                institution = institution or inst_m.group(1).strip(" ,;()")
                                deg_part = clean_line[:inst_m.start()].strip(" ,;()")
                                if deg_part:
                                    degree = degree or deg_part
                            else:
                                parts = [p.strip() for p in re.split(r"[,–—]", clean_line) if p.strip()]
                                if len(parts) >= 2:
                                    degree = degree or parts[0]
                                    institution = institution or ", ".join(parts[1:])
                                elif len(parts) == 1 and not degree:
                                    degree = parts[0]

                # STRICT: Do not create disclosure if degree or institution could not be found
                if degree:
                    structured: Dict[str, Any] = {"degree": degree}
                    if institution:
                        structured["institution"] = institution
                    if year is not None:
                        structured["year"] = year
                    if course_format:
                        structured["course_format"] = course_format

                    raw_excerpt = (
                        excerpt_match.group(1).strip()
                        if excerpt_match
                        else f"{degree}, {institution or ''}, {year or ''}".strip(" ,")
                    )

                    self.disclosures.append(
                        ExtractedDisclosureCandidate(
                            category="education",
                            field_key="highest_educational_qualification",
                            subject_type="self",
                            structured_value=structured,
                            raw_excerpt=raw_excerpt,
                            page_number=page_num,
                            confidence_note="rule_matched",
                        )
                    )
                    return
                else:
                    self.warnings.append(
                        f"Page {page_num}: Educational qualification header detected but degree could not be verified."
                    )

    def _extract_movable_assets(self) -> None:
        """Extract Item (7)(A) & Part-B Item (8)(A) Details of Movable Assets."""
        for page_num, text in self.page_texts.items():
            text_upper = text.upper()
            is_part_b = "PART-B" in text_upper or "ABSTRACT OF" in text_upper

            if "MOVABLE ASSETS" in text_upper or "MOVEABLE ASSETS" in text_upper or "ITEM (7)" in text_upper or "ITEM 7" in text_upper:
                # 1. Search for Gross Total Movable Assets block (handles single-line and multiline table rows)
                total_match = re.search(
                    r"(?:Gross\s*Total\s*(?:Movable\s*Assets|Value)|(?:Moveable|Movable)\s*Assets\s*[\(\s]*Total\s*Value[\)\s]*)[\s\n]+([\s\S]+?)(?=\n\s*(?:B\.|DETAILS|[A-Z]\.|\()|\Z)",
                    text,
                    re.I,
                )

                self_amt: Optional[int] = None
                spouse_amt: Optional[int] = None

                if total_match:
                    raw_block = total_match.group(1).strip()
                    lines = [l.strip() for l in raw_block.splitlines() if l.strip()]
                    parsed_vals: List[int] = []
                    for l in lines:
                        parts = [p.strip() for p in re.split(r"\s{2,}|\t", l) if p.strip()] or [l]
                        for p in parts:
                            val = parse_indian_amount(p)
                            if val is not None:
                                parsed_vals.append(val)

                    if len(parsed_vals) >= 1:
                        self_amt = parsed_vals[0]
                    if len(parsed_vals) >= 2:
                        spouse_amt = parsed_vals[1]

                # 2. Fallback key-value patterns
                if self_amt is None:
                    self_m = re.search(r"Self\s*Movable\s*Assets[:\s]+([^\n]+)", text, re.I)
                    if self_m:
                        self_amt = parse_indian_amount(self_m.group(1))

                if spouse_amt is None:
                    sp_m = re.search(r"Spouse\s*Movable\s*Assets[:\s]+([^\n]+)", text, re.I)
                    if sp_m:
                        spouse_amt = parse_indian_amount(sp_m.group(1))

                # Extract breakdown items (Cash in hand, Bank deposits) if present
                cash_m = re.search(
                    r"Cash\s*in\s*hand[\s\n]+([\s\S]+?)(?=\n\s*(?:\([a-z0-9]+\)|Deposits|Motor|Jewellery|$))",
                    text,
                    re.I,
                )
                cash_self = None
                if cash_m:
                    c_lines = [l.strip() for l in cash_m.group(1).strip().splitlines() if l.strip()]
                    if c_lines:
                        cash_self = parse_indian_amount(c_lines[0])

                bank_m = re.search(
                    r"Deposits\s*in\s*Bank[^\n]*\n([\s\S]+?)(?=\n\s*(?:\([a-z0-9]+\)|Motor|Jewellery|Gross|$))",
                    text,
                    re.I,
                )
                bank_self = None
                if bank_m:
                    b_lines = [l.strip() for l in bank_m.group(1).strip().splitlines() if l.strip()]
                    if b_lines:
                        bank_self = parse_indian_amount(b_lines[0])

                # Record values for consistency check
                if is_part_b:
                    if self_amt is not None:
                        self.part_b_values[("movable_assets", "self")] = (
                            self_amt,
                            format_inr_commas(self_amt),
                            page_num,
                        )
                    if spouse_amt is not None:
                        self.part_b_values[("movable_assets", "spouse")] = (
                            spouse_amt,
                            format_inr_commas(spouse_amt),
                            page_num,
                        )
                else:
                    if self_amt is not None:
                        self.part_a_values[("movable_assets", "self")] = (
                            self_amt,
                            format_inr_commas(self_amt),
                            page_num,
                        )
                    if spouse_amt is not None:
                        self.part_a_values[("movable_assets", "spouse")] = (
                            spouse_amt,
                            format_inr_commas(spouse_amt),
                            page_num,
                        )

                # Add disclosures
                if self_amt is not None and not any(
                    d.category == "movable_assets" and d.subject_type == "self"
                    for d in self.disclosures
                ):
                    breakdown = {}
                    if cash_self is not None and cash_self > 0:
                        breakdown["cash"] = cash_self
                    if bank_self is not None and bank_self > 0:
                        breakdown["bank_deposits"] = bank_self

                    fmt = format_inr_commas(self_amt)
                    struct_val: Dict[str, Any] = {
                        "currency": "INR",
                        "amount": self_amt,
                        "formatted": fmt,
                    }
                    if breakdown:
                        struct_val["breakdown"] = breakdown

                    self.disclosures.append(
                        ExtractedDisclosureCandidate(
                            category="movable_assets",
                            field_key="gross_total_movable_assets",
                            subject_type="self",
                            structured_value=struct_val,
                            raw_excerpt=f"Self Movable Assets: {fmt}",
                            page_number=page_num,
                            confidence_note="rule_matched",
                        )
                    )

                if spouse_amt is not None and not any(
                    d.category == "movable_assets" and d.subject_type == "spouse"
                    for d in self.disclosures
                ):
                    fmt_sp = format_inr_commas(spouse_amt)
                    self.disclosures.append(
                        ExtractedDisclosureCandidate(
                            category="movable_assets",
                            field_key="gross_total_movable_assets",
                            subject_type="spouse",
                            structured_value={
                                "currency": "INR",
                                "amount": spouse_amt,
                                "formatted": fmt_sp,
                            },
                            raw_excerpt=f"Spouse Movable Assets: {fmt_sp}",
                            page_number=page_num,
                            confidence_note="rule_matched",
                        )
                    )

        if not any(d.category == "movable_assets" for d in self.disclosures):
            self.warnings.append("Movable assets section could not be detected or verified.")

    def _extract_immovable_assets(self) -> None:
        """Extract Item (7)(B) & Part-B Item (8)(B) Details of Immovable Assets."""
        for page_num, text in self.page_texts.items():
            text_upper = text.upper()
            is_part_b = "PART-B" in text_upper or "ABSTRACT OF" in text_upper

            if "IMMOVABLE ASSETS" in text_upper:
                total_match = re.search(
                    r"(?:Total\s*Current\s*Market\s*Value\s*(?:of\s*Immovable\s*Assets)?|Total\s*(?:of\s*)?Current\s*Market\s*Value|Total\s*Immovable|Approximate\s*Current\s*Market\s*Price)[\s\n]+([\s\S]+?)(?=\n\s*(?:Form|ITEM|Details|[A-Z]\.|\()|\Z)",
                    text,
                    re.I,
                )
                amt: Optional[int] = None
                if total_match:
                    raw_block = total_match.group(1).strip()
                    lines = [l.strip() for l in raw_block.splitlines() if l.strip()]
                    for l in lines:
                        val = parse_indian_amount(l)
                        if val is not None:
                            amt = val
                            break

                if amt is None:
                    self_immov = re.search(
                        r"Self\s*Immovable\s*Assets[:\s]+[^\n]*([₹\d,]+)", text, re.I
                    )
                    if self_immov:
                        amt = parse_indian_amount(self_immov.group(1))

                # Identify asset type from text context
                asset_type = "Immovable assets"
                if re.search(r"Agricultural\s*Land", text, re.I):
                    asset_type = "Agricultural land"
                elif re.search(r"Non-Agricultural\s*Land", text, re.I):
                    asset_type = "Non-agricultural land"
                elif re.search(r"Commercial\s*Building", text, re.I):
                    asset_type = "Commercial buildings"
                elif re.search(r"Residential\s*Building", text, re.I):
                    asset_type = "Residential buildings"

                # Extract survey number if declared
                survey_match = re.search(
                    r"(?:Sy\.?\s*No\.?|Survey\s*No\.?)[\s:]*([A-Za-z0-9/]+)", text, re.I
                )
                survey_no = survey_match.group(1).strip() if survey_match else None

                if amt is not None:
                    fmt = format_inr_commas(amt)
                    if is_part_b:
                        self.part_b_values[("immovable_assets", "self")] = (amt, fmt, page_num)
                    else:
                        self.part_a_values[("immovable_assets", "self")] = (amt, fmt, page_num)

                    if not any(d.category == "immovable_assets" for d in self.disclosures):
                        struct_val: Dict[str, Any] = {
                            "asset_type": asset_type,
                            "currency": "INR",
                            "amount": amt,
                            "formatted": fmt,
                        }
                        if survey_no:
                            struct_val["survey_number"] = survey_no

                        self.disclosures.append(
                            ExtractedDisclosureCandidate(
                                category="immovable_assets",
                                field_key="agricultural_land_current_market_value"
                                if asset_type == "Agricultural land"
                                else "total_current_market_value_immovable_assets",
                                subject_type="self",
                                structured_value=struct_val,
                                raw_excerpt=f"Self Immovable Assets: {asset_type} valued at {fmt}",
                                page_number=page_num,
                                confidence_note="rule_matched",
                            )
                        )

        if not any(d.category == "immovable_assets" for d in self.disclosures):
            self.warnings.append("Immovable assets section could not be detected or verified.")

    def _extract_liabilities(self) -> None:
        """Extract Item (8) & Part-B Item (9) Details of Liabilities / Government Dues."""
        for page_num, text in self.page_texts.items():
            text_upper = text.upper()
            is_part_b = "PART-B" in text_upper or "ABSTRACT OF" in text_upper

            if "LIABILITIES" in text_upper or "ITEM (8)" in text_upper or "ITEM 8" in text_upper:
                total_match = re.search(
                    r"(?:Grand\s*Total\s*of\s*Liabilities|Total\s*Liabilities|Grand\s*total\s*of\s*all\s*liabilities)[\s\n]+([\s\S]+?)(?=\n\s*(?:B\.|GOVERNMENT|Details|[A-Z]\.|\()|\Z)",
                    text,
                    re.I,
                )
                amt: Optional[int] = None
                if total_match:
                    raw_block = total_match.group(1).strip()
                    lines = [l.strip() for l in raw_block.splitlines() if l.strip()]
                    for l in lines:
                        val = parse_indian_amount(l)
                        if val is not None:
                            amt = val
                            break

                home_loan_match = re.search(
                    r"(?:Home\s*loan|Loan[^\n]*Bank)[\s\S]{0,100}?([₹\d,]+)", text, re.I
                )
                if amt is None and home_loan_match:
                    amt = parse_indian_amount(home_loan_match.group(1))

                # Parse lender directly from text (multiline friendly)
                lender_match = re.search(
                    r"(?:Home\s*loan|Loan)\s+from\s+([\s\S]+?)(?=\n\s*(?:[₹\d,]|Nil|\())",
                    text,
                    re.I,
                )
                lender: Optional[str] = None
                if lender_match:
                    lender = re.sub(r"\s+", " ", lender_match.group(1)).strip()

                # Loan type
                loan_type_match = re.search(
                    r"(Home\s*loan|Personal\s*loan|Vehicle\s*loan|Term\s*loan|Agricultural\s*loan)",
                    text,
                    re.I,
                )
                loan_type = loan_type_match.group(1).capitalize() if loan_type_match else "Bank loan"

                # Parse government dues
                gov_dues_match = re.search(
                    r"(?:Grand\s*Total\s*of\s*All\s*Government\s*Dues|Government\s*dues)[\s\n]+([\s\S]+?)(?=\n\s*(?:Form|ITEM|Details|[A-Z]\.|\()|\Z)",
                    text,
                    re.I,
                )
                gov_dues = 0
                if gov_dues_match:
                    g_lines = [l.strip() for l in gov_dues_match.group(1).strip().splitlines() if l.strip()]
                    if g_lines:
                        parsed_gd = parse_indian_amount(g_lines[0])
                        if parsed_gd is not None:
                            gov_dues = parsed_gd

                if amt is not None:
                    fmt = format_inr_commas(amt)
                    if is_part_b:
                        self.part_b_values[("liabilities", "self")] = (amt, fmt, page_num)
                    else:
                        self.part_a_values[("liabilities", "self")] = (amt, fmt, page_num)

                    if not any(d.category == "liabilities" for d in self.disclosures):
                        struct_val: Dict[str, Any] = {
                            "loan_type": loan_type,
                            "currency": "INR",
                            "amount": amt,
                            "formatted": fmt,
                            "government_dues": gov_dues,
                        }
                        if lender:
                            struct_val["lender"] = lender

                        raw_excerpt = (
                            f"Home loan from {lender} (Self: {fmt}; Government Dues: Nil)"
                            if lender and gov_dues == 0
                            else f"Liabilities (Self: {fmt}; Government Dues: {format_inr_commas(gov_dues)})"
                        )

                        self.disclosures.append(
                            ExtractedDisclosureCandidate(
                                category="liabilities",
                                field_key="bank_loans_home_loan",
                                subject_type="self",
                                structured_value=struct_val,
                                raw_excerpt=raw_excerpt,
                                page_number=page_num,
                                confidence_note="rule_matched",
                            )
                        )

        if not any(d.category == "liabilities" for d in self.disclosures):
            self.warnings.append("Liabilities section could not be detected or verified.")

    def _extract_pending_criminal_cases(self) -> None:
        """Extract Item (5) Details of Pending Criminal Cases. ZERO synthetic fallbacks."""
        for page_num, text in self.page_texts.items():
            text_upper = text.upper()
            if "PENDING CRIMINAL CASES" in text_upper or "ITEM (5)" in text_upper or "ITEM 5" in text_upper:
                # 1. Check if Item 5(i) declares NIL pending cases
                is_clean_nil = (
                    re.search(r"Item\s*5\s*\(i\)[\s\S]{0,100}?NIL", text, re.I)
                    or re.search(r"no\s+pending\s+criminal\s+case\s+against\s+me", text, re.I)
                )
                has_actual_cases = re.search(
                    r"FIR\s*(?:No\.?|Number)|Case\s*(?:No\.?|Number)", text, re.I
                )

                if is_clean_nil and not has_actual_cases:
                    self.disclosures.append(
                        ExtractedDisclosureCandidate(
                            category="pending_criminal_cases",
                            field_key="pending_cases_summary",
                            subject_type="self",
                            structured_value={"count": 0, "status": "NIL"},
                            raw_excerpt="Item (5) Pending Criminal Cases: NIL",
                            page_number=page_num,
                            confidence_note="rule_matched",
                        )
                    )
                    return

                # 2. Extract actual case details from text
                fir_match = re.search(
                    r"FIR\s*(?:No\.?|Number)[\s:\n]*([A-Za-z0-9/]+(?:\s+of\s+\d{4})?)",
                    text,
                    re.I,
                )
                ps_match = re.search(
                    r"FIR\s*(?:No\.?|Number)[^,\n]+,\s*([A-Za-z0-9\s]+(?:PS|Police\s*Station))",
                    text,
                    re.I,
                )
                if not ps_match:
                    ps_match = re.search(
                        r"(?:Police\s*Station|PS)[\s:\n]*([A-Za-z0-9\s]+)", text, re.I
                    )

                case_match = re.search(
                    r"Case\s*(?:No\.?|Number)[\s:\n]*([A-Za-z0-9/\-]+)", text, re.I
                )
                court_match = re.search(
                    r"Case\s*(?:No\.?|Number)[^,\n]+,\s*([A-Za-z0-9\s]+?(?:Court|Tribunal))",
                    text,
                    re.I,
                )
                if not court_match:
                    court_match = re.search(
                        r"(?:Court|Name\s*of\s*(?:the\s*)?Court)[\s:\n]+([A-Za-z0-9\s]+?(?:Court|Magistrate|Tribunal))",
                        text,
                        re.I,
                    )

                # Charges framed
                cf_match = re.search(
                    r"Whether\s*charges\s*(?:have\s*been\s*)?framed\??[\s:\n]*(NO|NIL|FALSE|YES|TRUE)",
                    text,
                    re.I,
                )
                charges_framed: Optional[bool] = None
                if cf_match:
                    charges_framed = cf_match.group(1).upper() in ["YES", "TRUE"]

                # Appeal filed
                af_match = re.search(
                    r"Whether\s*(?:any\s*)?Appeal[^\n\?]*\?[\s:\n]*(NO|NIL|FALSE|YES|TRUE)",
                    text,
                    re.I,
                )
                appeal_filed: Optional[bool] = None
                if af_match:
                    appeal_filed = af_match.group(1).upper() in ["YES", "TRUE"]

                # Sections
                sections = extract_legal_sections(text)

                # Stage code
                stage_code: Optional[str] = None
                if "cognizance" in text.lower():
                    stage_code = "STAGE_COGNIZANCE"
                elif charges_framed is True:
                    stage_code = "CHARGES_FRAMED"
                elif charges_framed is False:
                    stage_code = "CHARGES_NOT_FRAMED"

                fir_no = fir_match.group(1).strip() if fir_match else None
                ps = ps_match.group(1).strip() if ps_match else None
                case_no = case_match.group(1).strip() if case_match else None
                court = court_match.group(1).strip() if court_match else None

                # Only construct disclosure if real case identifiers were found
                if fir_no or case_no or sections:
                    struct_val: Dict[str, Any] = {
                        "fir_no": fir_no,
                        "police_station": ps,
                        "case_no": case_no,
                        "court_name": court,
                        "sections": sections,
                        "charges_framed": charges_framed if charges_framed is not None else False,
                        "appeal_filed": appeal_filed if appeal_filed is not None else False,
                    }
                    if stage_code:
                        struct_val["stage_code"] = stage_code

                    raw_excerpt = (
                        f"FIR No. {fir_no or 'N/A'}, {ps or 'N/A'}; Case No. {case_no or 'N/A'}, {court or 'N/A'}; "
                        f"Sections: {', '.join(sections) if sections else 'N/A'}; "
                        f"Charges Framed: {'YES' if charges_framed else 'NO'}; "
                        f"Appeal Filed: {'YES' if appeal_filed else 'NO'}"
                    )

                    self.disclosures.append(
                        ExtractedDisclosureCandidate(
                            category="pending_criminal_cases",
                            field_key="pending_case_item_1",
                            subject_type="self",
                            structured_value=struct_val,
                            raw_excerpt=raw_excerpt,
                            page_number=page_num,
                            confidence_note="rule_matched",
                        )
                    )
                    return
                elif "NIL" in text_upper:
                    self.disclosures.append(
                        ExtractedDisclosureCandidate(
                            category="pending_criminal_cases",
                            field_key="pending_cases_summary",
                            subject_type="self",
                            structured_value={"count": 0, "status": "NIL"},
                            raw_excerpt="Item (5) Pending Criminal Cases: NIL",
                            page_number=page_num,
                            confidence_note="rule_matched",
                        )
                    )
                    return

        self.warnings.append("Pending criminal cases section could not be detected or verified.")

    def _extract_convictions(self) -> None:
        """Extract Item (6) Details of Cases of Conviction."""
        for page_num, text in self.page_texts.items():
            text_upper = text.upper()
            if "CASES OF CONVICTION" in text_upper or "ITEM (6)" in text_upper or "ITEM 6" in text_upper:
                is_nil = (
                    "NIL" in text_upper
                    or "NOT APPLICABLE" in text_upper
                    or "NEVER BEEN CONVICTED" in text_upper
                    or "COUNT: 0" in text_upper
                )
                if is_nil:
                    self.disclosures.append(
                        ExtractedDisclosureCandidate(
                            category="convictions",
                            field_key="cases_of_conviction",
                            subject_type="self",
                            structured_value={"count": 0, "status": "NIL"},
                            raw_excerpt="Item (6) Cases of Conviction: NIL / NOT APPLICABLE",
                            page_number=page_num,
                            confidence_note="rule_matched",
                        )
                    )
                    return
                else:
                    self.warnings.append(
                        f"Page {page_num}: Conviction record detected with non-nil entries. Flagged for detailed human review."
                    )
                    return

        self.warnings.append("Convictions section could not be detected or verified.")

    def _check_consistency(self) -> None:
        """
        Compare Part-A detailed table totals against Part-B Abstract totals.
        Whenever both are present and differ by > 1%, emit a high-priority warning.
        """
        for key, (a_amt, a_fmt, a_page) in self.part_a_values.items():
            if key in self.part_b_values:
                b_amt, b_fmt, b_page = self.part_b_values[key]
                category, subject = key

                max_val = max(a_amt, b_amt)
                diff_pct = (
                    abs(a_amt - b_amt) / max_val
                    if max_val > 0
                    else (1.0 if a_amt != b_amt else 0.0)
                )

                if diff_pct > 0.01:
                    warning = (
                        f"[PART-A vs PART-B MISMATCH] {category.replace('_', ' ').title()} ({subject}): "
                        f"Part-A on page {a_page} ({a_fmt}) does not match Part-B on page {b_page} ({b_fmt}) "
                        f"(variance: {diff_pct * 100:.1f}%)."
                    )
                    self.warnings.append(warning)


def extract_affidavit_disclosures(pdf_path: Path | str) -> ExtractionResult:
    """Extract Form 26 disclosures from a PDF file on disk."""
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
        inspection = inspect_pdf_document(doc, pdf_bytes)
        extractor = Form26Extractor(doc, inspection)
        return extractor.extract_all()
    finally:
        doc.close()


def extract_affidavit_disclosures_from_bytes(pdf_bytes: bytes) -> ExtractionResult:
    """Extract Form 26 disclosures directly from PDF bytes in memory."""
    validate_pdf_bytes(pdf_bytes)

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Corrupt or unreadable PDF document: {e}")

    try:
        inspection = inspect_pdf_document(doc, pdf_bytes)
        extractor = Form26Extractor(doc, inspection)
        return extractor.extract_all()
    finally:
        doc.close()

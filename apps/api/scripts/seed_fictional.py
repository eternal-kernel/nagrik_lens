#!/usr/bin/env python3
"""Idempotent seed script for Nagrik Lens fictional test data.

Initializes the SQLite database schema, loads the legal glossary,
verifies/generates the synthetic Form 26 PDF fixture, and populates
fictional candidate disclosures with strict Form 26 alignment.
"""

from datetime import date
import hashlib
import json
from pathlib import Path
import sys

# Ensure apps/api is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
API_DIR = SCRIPT_DIR.parent
WORKSPACE_ROOT = API_DIR.parent.parent

if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from sqlalchemy import func, select
from app.core.database import SessionLocal, init_db
from app.models import (
    Affidavit,
    Candidate,
    Constituency,
    Disclosure,
    Election,
    LegalGlossary,
    ReviewEvent,
)
from scripts.generate_fictional_pdf import generate_fictional_pdf


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def seed_database() -> dict:
    """Idempotently seed the Nagrik Lens database."""
    print("--- Initializing Nagrik Lens Database Schema ---")
    init_db()

    # Step 1: Ensure PDF fixture exists and compute hash
    pdf_path = WORKSPACE_ROOT / "fixtures" / "fictional" / "candidate_x_affidavit.pdf"
    if not pdf_path.exists():
        print(f"Generating synthetic PDF fixture at: {pdf_path}")
        generate_fictional_pdf(pdf_path)
    else:
        print(f"Synthetic PDF fixture already present at: {pdf_path}")

    file_hash = compute_sha256(pdf_path)
    print(f"Affidavit SHA-256: {file_hash}")

    db = SessionLocal()
    try:
        # Step 2: Load Legal Glossary JSON
        glossary_path = WORKSPACE_ROOT / "data" / "glossary" / "legal_terms.json"
        if not glossary_path.exists():
            raise FileNotFoundError(f"Glossary JSON not found at: {glossary_path}")

        with open(glossary_path, "r", encoding="utf-8") as gf:
            glossary_data = json.load(gf)

        print(f"Loading {len(glossary_data)} legal glossary entries...")
        for entry in glossary_data:
            glossary_item = db.execute(
                select(LegalGlossary).where(LegalGlossary.code_key == entry["code_key"])
            ).scalar_one_or_none()

            if glossary_item is None:
                glossary_item = LegalGlossary(
                    code_key=entry["code_key"],
                    act_name=entry["act_name"],
                    term_en=entry["term_en"],
                    explanation_en=entry["explanation_en"],
                    explanation_te=entry["explanation_te"],
                    explanation_hi=entry["explanation_hi"],
                    review_status=entry.get("review_status", "verified"),
                )
                db.add(glossary_item)
            else:
                glossary_item.act_name = entry["act_name"]
                glossary_item.term_en = entry["term_en"]
                glossary_item.explanation_en = entry["explanation_en"]
                glossary_item.explanation_te = entry["explanation_te"]
                glossary_item.explanation_hi = entry["explanation_hi"]
                glossary_item.review_status = entry.get("review_status", "verified")

        db.flush()

        # Step 3: Seed Election
        election_name = "Telangana Legislative Assembly General Election 2024 (Fictional Sample)"
        election = db.execute(
            select(Election).where(Election.name == election_name)
        ).scalar_one_or_none()

        if election is None:
            election = Election(
                name=election_name,
                election_type="Assembly",
                year=2024,
                state="Telangana",
            )
            db.add(election)
            db.flush()
            print(f"Created Election: {election.name} (id={election.id})")
        else:
            election.election_type = "Assembly"
            election.year = 2024
            election.state = "Telangana"
            print(f"Existing Election found: {election.name} (id={election.id})")

        # Step 4: Seed Constituency
        constituency_code = "FC-01"
        constituency = db.execute(
            select(Constituency).where(
                Constituency.election_id == election.id,
                Constituency.code == constituency_code,
            )
        ).scalar_one_or_none()

        if constituency is None:
            constituency = Constituency(
                election_id=election.id,
                name="Fictional Constituency",
                code=constituency_code,
                state="Telangana",
            )
            db.add(constituency)
            db.flush()
            print(f"Created Constituency: {constituency.name} (id={constituency.id})")
        else:
            constituency.name = "Fictional Constituency"
            constituency.state = "Telangana"
            print(f"Existing Constituency found: {constituency.name} (id={constituency.id})")

        # Step 5: Seed Candidate
        candidate_name = "Candidate X"
        candidate = db.execute(
            select(Candidate).where(
                Candidate.constituency_id == constituency.id,
                Candidate.name == candidate_name,
            )
        ).scalar_one_or_none()

        if candidate is None:
            candidate = Candidate(
                constituency_id=constituency.id,
                name=candidate_name,
                display_name="Candidate X (Fictional Sample)",
                party_name="Independent — Fictional",
                is_fictional=True,
            )
            db.add(candidate)
            db.flush()
            print(f"Created Candidate: {candidate.display_name} (id={candidate.id})")
        else:
            candidate.display_name = "Candidate X (Fictional Sample)"
            candidate.party_name = "Independent — Fictional"
            candidate.is_fictional = True
            print(f"Existing Candidate found: {candidate.display_name} (id={candidate.id})")

        # Step 6: Seed Affidavit
        relative_pdf_path = "fixtures/fictional/candidate_x_affidavit.pdf"
        affidavit = db.execute(
            select(Affidavit).where(
                Affidavit.candidate_id == candidate.id,
                Affidavit.file_path == relative_pdf_path,
            )
        ).scalar_one_or_none()

        if affidavit is None:
            affidavit = Affidavit(
                candidate_id=candidate.id,
                source_url="https://eci.gov.in/fictional/candidate_x_form26.pdf",
                file_path=relative_pdf_path,
                file_hash=file_hash,
                filing_date=date(2024, 4, 15),
                processing_status="processed",
                publication_status="pending_review",
                redaction_boxes=None,
            )
            db.add(affidavit)
            db.flush()
            print(f"Created Affidavit (id={affidavit.id}) for Candidate X")
        else:
            affidavit.file_hash = file_hash
            affidavit.filing_date = date(2024, 4, 15)
            affidavit.processing_status = "processed"
            affidavit.publication_status = "pending_review"
            print(f"Existing Affidavit found (id={affidavit.id}) for Candidate X")

        # Step 7: Seed 7 Disclosures matching exact Form 26 specifications
        # NOTE: 6 are 'verified' and 1 (Spouse Movable Assets) is 'needs_review'
        raw_disclosures = [
            # 1. Education (Page 1)
            {
                "category": "education",
                "field_key": "highest_educational_qualification",
                "subject_type": "self",
                "page_number": 1,
                "verification_status": "verified",
                "structured_value": {
                    "degree": "B.Com",
                    "institution": "Osmania University",
                    "year": 2012,
                    "course_format": "Regular Full-Time Degree",
                },
                "raw_excerpt": 'B.Com, Osmania University, 2012',
                "review_action": "verified",
                "review_note": "Educational qualification matches Osmania University degree certificate.",
            },
            # 2. Movable Assets - Self (Page 2)
            {
                "category": "movable_assets",
                "field_key": "gross_total_movable_assets",
                "subject_type": "self",
                "page_number": 2,
                "verification_status": "verified",
                "structured_value": {
                    "currency": "INR",
                    "amount": 500000,
                    "formatted": "₹5,00,000",
                    "breakdown": {
                        "cash": 50000,
                        "bank_deposits": 250000,
                        "motor_vehicles": 100000,
                        "jewellery": 100000,
                    },
                },
                "raw_excerpt": "Self Movable Assets: ₹5,00,000",
                "review_action": "verified",
                "review_note": "Self movable assets total matches Item (7)(A) subtotal table.",
            },
            # 3. Movable Assets - Spouse (Page 2) -> NEEDS_REVIEW
            {
                "category": "movable_assets",
                "field_key": "gross_total_movable_assets",
                "subject_type": "spouse",
                "page_number": 2,
                "verification_status": "needs_review",  # CRITICAL: Publication gate test item
                "structured_value": {
                    "currency": "INR",
                    "amount": 320000,
                    "formatted": "₹3,20,000",
                    "breakdown": {
                        "cash": 20000,
                        "bank_deposits": 150000,
                        "motor_vehicles": 50000,
                        "jewellery": 100000,
                    },
                },
                "raw_excerpt": "Spouse Movable Assets: ₹3,20,000",
                "review_action": "flagged",
                "review_note": "Flagged for second review: bank deposit interest certificate copy pending verification.",
            },
            # 4. Immovable Assets - Self (Page 2)
            {
                "category": "immovable_assets",
                "field_key": "agricultural_land_current_market_value",
                "subject_type": "self",
                "page_number": 2,
                "verification_status": "verified",
                "structured_value": {
                    "asset_type": "Agricultural land",
                    "survey_number": "99/A",
                    "location": "Fictional Village, Telangana",
                    "extent_acres": 2.0,
                    "currency": "INR",
                    "amount": 1800000,
                    "formatted": "₹18,00,000",
                },
                "raw_excerpt": "Self Immovable Assets: Agricultural land valued at ₹18,00,000",
                "review_action": "verified",
                "review_note": "Agricultural land survey number 99/A valuation verified.",
            },
            # 5. Liabilities - Self (Page 3)
            {
                "category": "liabilities",
                "field_key": "bank_loans_home_loan",
                "subject_type": "self",
                "page_number": 3,
                "verification_status": "verified",
                "structured_value": {
                    "loan_type": "Home loan",
                    "lender": "Public Sector Bank (Fictional National Bank, Main Branch)",
                    "currency": "INR",
                    "amount": 650000,
                    "formatted": "₹6,50,000",
                    "government_dues": 0,
                },
                "raw_excerpt": "Home loan from Public Sector Bank (Self: ₹6,50,000; Government Dues: Nil)",
                "review_action": "verified",
                "review_note": "Home loan principal balance confirmed against bank statement excerpt.",
            },
            # 6. Pending Criminal Cases (Page 4)
            {
                "category": "pending_criminal_cases",
                "field_key": "pending_case_item_1",
                "subject_type": "self",
                "page_number": 4,
                "verification_status": "verified",
                "structured_value": {
                    "fir_no": "112/2022",
                    "police_station": "Fictional PS",
                    "case_no": "CC/450/2023",
                    "court_name": "Judicial First Class Magistrate Court",
                    "sections": ["IPC 143", "IPC 341"],
                    "charges_framed": False,
                    "appeal_filed": False,
                    "stage_code": "STAGE_COGNIZANCE",
                },
                "raw_excerpt": "FIR No. 112/2022, Fictional PS; Case No. CC/450/2023, Judicial First Class Magistrate Court; Sections: IPC 143, IPC 341; Charges Framed: NO; Appeal Filed: NO",
                "review_action": "verified",
                "review_note": "Verified: charges are not framed; cognizance stage verified against court docket.",
            },
            # 7. Convictions (Page 4)
            {
                "category": "convictions",
                "field_key": "cases_of_conviction",
                "subject_type": "self",
                "page_number": 4,
                "verification_status": "verified",
                "structured_value": {
                    "count": 0,
                    "status": "NIL",
                },
                "raw_excerpt": "Item (6) Cases of Conviction: NIL / NOT APPLICABLE",
                "review_action": "verified",
                "review_note": "Deponent declared Nil convictions under Rule 4A.",
            },
        ]

        print(f"Seeding {len(raw_disclosures)} disclosures...")
        for disc_def in raw_disclosures:
            disc = db.execute(
                select(Disclosure).where(
                    Disclosure.affidavit_id == affidavit.id,
                    Disclosure.category == disc_def["category"],
                    Disclosure.field_key == disc_def["field_key"],
                    Disclosure.subject_type == disc_def["subject_type"],
                )
            ).scalar_one_or_none()

            is_new = False
            if disc is None:
                disc = Disclosure(
                    affidavit_id=affidavit.id,
                    category=disc_def["category"],
                    field_key=disc_def["field_key"],
                    subject_type=disc_def["subject_type"],
                    structured_value=disc_def["structured_value"],
                    raw_excerpt=disc_def["raw_excerpt"],
                    page_number=disc_def["page_number"],
                    verification_status=disc_def["verification_status"],
                )
                db.add(disc)
                db.flush()
                is_new = True
            else:
                disc.structured_value = disc_def["structured_value"]
                disc.raw_excerpt = disc_def["raw_excerpt"]
                disc.page_number = disc_def["page_number"]
                disc.verification_status = disc_def["verification_status"]
                db.flush()

            # Record ReviewEvent if none exists for this disclosure action
            existing_event = db.execute(
                select(ReviewEvent).where(
                    ReviewEvent.disclosure_id == disc.id,
                    ReviewEvent.action == disc_def["review_action"],
                )
            ).scalar_one_or_none()

            if existing_event is None:
                review_event = ReviewEvent(
                    disclosure_id=disc.id,
                    reviewer_name="Audit Lead (Fictional)",
                    action=disc_def["review_action"],
                    previous_value=None if is_new else {"status": "draft"},
                    new_value={"status": disc_def["verification_status"]},
                    review_note=disc_def["review_note"],
                )
                db.add(review_event)

        db.commit()
        print("Database transaction successfully committed.")

        # Step 8: Compute summary statistics
        counts = {
            "elections": db.query(func.count(Election.id)).scalar(),
            "constituencies": db.query(func.count(Constituency.id)).scalar(),
            "candidates": db.query(func.count(Candidate.id)).scalar(),
            "affidavits": db.query(func.count(Affidavit.id)).scalar(),
            "disclosures": db.query(func.count(Disclosure.id)).scalar(),
            "legal_glossary": db.query(func.count(LegalGlossary.id)).scalar(),
            "review_events": db.query(func.count(ReviewEvent.id)).scalar(),
        }

        status_breakdown = dict(
            db.query(Disclosure.verification_status, func.count(Disclosure.id))
            .group_by(Disclosure.verification_status)
            .all()
        )

        return {
            "table_counts": counts,
            "disclosure_status_breakdown": status_breakdown,
        }
    finally:
        db.close()


if __name__ == "__main__":
    results = seed_database()
    print("\n================ SEED SUMMARY ================")
    print("Table Row Counts:")
    for table_name, count in results["table_counts"].items():
        print(f"  {table_name}: {count}")
    print("\nDisclosure Status Breakdown:")
    for status, count in results["disclosure_status_breakdown"].items():
        print(f"  {status}: {count}")
    print("==============================================")

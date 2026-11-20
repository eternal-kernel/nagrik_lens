import json
from pathlib import Path
import pymupdf
import pytest
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


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_table_row_counts(db_session):
    """Verify exact expected row counts in all 7 tables."""
    assert db_session.query(func.count(Election.id)).scalar() == 1
    assert db_session.query(func.count(Constituency.id)).scalar() == 1
    assert db_session.query(func.count(Candidate.id)).scalar() == 1
    assert db_session.query(func.count(Affidavit.id)).scalar() == 1
    assert db_session.query(func.count(Disclosure.id)).scalar() == 7
    assert db_session.query(func.count(LegalGlossary.id)).scalar() == 4
    assert db_session.query(func.count(ReviewEvent.id)).scalar() == 7


def test_candidate_properties(db_session):
    """Verify Candidate X has is_fictional=True and valid foreign key hierarchy."""
    candidate = db_session.execute(select(Candidate)).scalar_one()
    assert candidate.name == "Candidate X"
    assert candidate.is_fictional is True
    assert candidate.party_name == "Independent — Fictional"
    assert candidate.constituency.code == "FC-01"
    assert candidate.constituency.election.name.startswith("Telangana Legislative Assembly")


def test_disclosure_verification_breakdown(db_session):
    """Verify 6 verified disclosures and exactly 1 needs_review (spouse movable assets)."""
    disclosures = db_session.execute(select(Disclosure)).scalars().all()
    assert len(disclosures) == 7

    verified_count = sum(1 for d in disclosures if d.verification_status == "verified")
    needs_review_count = sum(1 for d in disclosures if d.verification_status == "needs_review")

    assert verified_count == 6
    assert needs_review_count == 1

    # Check that the flagged disclosure is Spouse Movable Assets
    flagged = next(d for d in disclosures if d.verification_status == "needs_review")
    assert flagged.category == "movable_assets"
    assert flagged.subject_type == "spouse"
    assert flagged.page_number == 2
    assert flagged.structured_value["amount"] == 320000


def test_pending_criminal_cases_structure(db_session):
    """Verify pending_criminal_cases has exact required Form 26 structured keys."""
    case_disc = db_session.execute(
        select(Disclosure).where(Disclosure.category == "pending_criminal_cases")
    ).scalar_one()

    val = case_disc.structured_value
    assert val["fir_no"] == "112/2022"
    assert val["police_station"] == "Fictional PS"
    assert val["case_no"] == "CC/450/2023"
    assert val["court_name"] == "Judicial First Class Magistrate Court"
    assert val["sections"] == ["IPC 143", "IPC 341"]
    assert val["charges_framed"] is False
    assert val["appeal_filed"] is False
    assert val["stage_code"] == "STAGE_COGNIZANCE"
    assert case_disc.page_number == 4


def test_convictions_disclosure(db_session):
    """Verify convictions disclosure shows NIL record on page 4."""
    conv_disc = db_session.execute(
        select(Disclosure).where(Disclosure.category == "convictions")
    ).scalar_one()

    assert conv_disc.structured_value == {"count": 0, "status": "NIL"}
    assert conv_disc.page_number == 4
    assert conv_disc.verification_status == "verified"


def test_legal_glossary_content(db_session):
    """Verify legal glossary entries exist in EN, TE, HI."""
    glossary_items = db_session.execute(select(LegalGlossary)).scalars().all()
    keys = {item.code_key for item in glossary_items}
    assert keys == {"IPC_143", "IPC_341", "STAGE_COGNIZANCE", "CHARGES_NOT_FRAMED"}

    for item in glossary_items:
        assert item.explanation_en and len(item.explanation_en) > 10
        assert item.explanation_te and len(item.explanation_te) > 10
        assert item.explanation_hi and len(item.explanation_hi) > 10
        assert item.review_status == "verified"


def test_pdf_fixture_properties():
    """Verify synthetic PDF has 4 pages and cleanly contains rupee symbol and Form 26 content."""
    workspace_root = Path(__file__).resolve().parent.parent.parent.parent
    pdf_path = workspace_root / "fixtures" / "fictional" / "candidate_x_affidavit.pdf"

    assert pdf_path.exists()
    doc = pymupdf.open(str(pdf_path))
    assert len(doc) == 4

    p1_text = doc[0].get_text()
    assert "FICTIONAL SAMPLE — NOT A REAL CANDIDATE" in p1_text
    assert "Candidate X (Fictional Sample)" in p1_text
    assert "B.Com, Osmania University, 2012" in p1_text

    p2_text = doc[1].get_text()
    assert "₹5,00,000" in p2_text
    assert "₹3,20,000" in p2_text
    assert "₹18,00,000" in p2_text

    p3_text = doc[2].get_text()
    assert "₹6,50,000" in p3_text

    p4_text = doc[3].get_text()
    assert "FIR No. 112/2022" in p4_text
    assert "IPC 143" in p4_text
    assert "IPC 341" in p4_text
    assert "CASES OF CONVICTION" in p4_text
    doc.close()

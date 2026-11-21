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
    PublicActivityRecord,
    ReviewEvent,
)
from app.services.public_records import render_public_record_explanations


@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_table_row_counts(db_session):
    """Verify exact expected row counts in all 8 tables for multi-candidate seed."""
    assert db_session.query(func.count(Election.id)).scalar() == 1
    assert db_session.query(func.count(Constituency.id)).scalar() == 1
    assert db_session.query(func.count(Candidate.id)).scalar() == 3
    assert db_session.query(func.count(Affidavit.id)).scalar() == 3
    assert db_session.query(func.count(Disclosure.id)).scalar() == 13
    assert db_session.query(func.count(PublicActivityRecord.id)).scalar() == 6
    assert db_session.query(func.count(LegalGlossary.id)).scalar() == 4
    assert db_session.query(func.count(ReviewEvent.id)).scalar() == 13


def test_candidate_properties(db_session):
    """Verify Candidate X, Y, and Z properties, fictional flags, and prior office."""
    # Candidate X
    cand_x = db_session.execute(select(Candidate).where(Candidate.id == 1)).scalar_one()
    assert cand_x.name == "Candidate X"
    assert cand_x.display_name == "Candidate X (Fictional Sample)"
    assert cand_x.is_fictional is True
    assert cand_x.party_name == "Independent — Fictional"
    assert cand_x.prior_office_held == "MLA — Fictional Constituency (2019–2024)"
    assert cand_x.constituency.code == "FC-01"
    assert cand_x.constituency.election.name.startswith("Telangana Legislative Assembly")

    # Candidate Y
    cand_y = db_session.execute(select(Candidate).where(Candidate.id == 2)).scalar_one()
    assert cand_y.name == "Kiran Rao"
    assert cand_y.display_name == "Kiran Rao (Fictional Sample)"
    assert cand_y.is_fictional is True
    assert cand_y.party_name == "Civic Reform Front — Fictional"
    assert cand_y.prior_office_held == "MLA — Fictional Constituency (2019–2024)"
    assert cand_y.constituency_id == cand_x.constituency_id

    # Candidate Z
    cand_z = db_session.execute(select(Candidate).where(Candidate.id == 3)).scalar_one()
    assert cand_z.name == "Ananya Sharma"
    assert cand_z.display_name == "Ananya Sharma (Fictional Sample)"
    assert cand_z.is_fictional is True
    assert cand_z.party_name == "Progressive Alliance — Fictional"
    assert cand_z.prior_office_held is None
    assert cand_z.constituency_id == cand_x.constituency_id


def test_disclosure_verification_breakdown(db_session):
    """Verify total breakdown: 12 verified, exactly 1 needs_review (Candidate X spouse assets)."""
    disclosures = db_session.execute(select(Disclosure)).scalars().all()
    assert len(disclosures) == 13

    verified_count = sum(1 for d in disclosures if d.verification_status == "verified")
    needs_review_count = sum(1 for d in disclosures if d.verification_status == "needs_review")

    assert verified_count == 12
    assert needs_review_count == 1

    # Check Candidate X specifically (6 verified + 1 needs_review)
    cand_x_discs = [d for d in disclosures if d.affidavit_id == 1]
    assert len(cand_x_discs) == 7
    assert sum(1 for d in cand_x_discs if d.verification_status == "verified") == 6
    assert sum(1 for d in cand_x_discs if d.verification_status == "needs_review") == 1

    # Check that the flagged disclosure is Candidate X's Spouse Movable Assets
    flagged = next(d for d in cand_x_discs if d.verification_status == "needs_review")
    assert flagged.category == "movable_assets"
    assert flagged.subject_type == "spouse"
    assert flagged.page_number == 2
    assert flagged.structured_value["amount"] == 320000

    # Candidate Y and Z disclosures are all verified
    cand_y_discs = [d for d in disclosures if d.affidavit_id == 2]
    assert len(cand_y_discs) == 3
    assert all(d.verification_status == "verified" for d in cand_y_discs)

    cand_z_discs = [d for d in disclosures if d.affidavit_id == 3]
    assert len(cand_z_discs) == 3
    assert all(d.verification_status == "verified" for d in cand_z_discs)


def test_pending_criminal_cases_structure(db_session):
    """Verify Candidate X pending_criminal_cases has exact required Form 26 structured keys."""
    case_disc = db_session.execute(
        select(Disclosure).where(
            Disclosure.affidavit_id == 1,
            Disclosure.category == "pending_criminal_cases",
        )
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

    # Candidate Z has pending cases NIL
    cand_z_case = db_session.execute(
        select(Disclosure).where(
            Disclosure.affidavit_id == 3,
            Disclosure.category == "pending_criminal_cases",
        )
    ).scalar_one()
    assert cand_z_case.structured_value == {"count": 0, "status": "NIL"}


def test_convictions_disclosure(db_session):
    """Verify convictions disclosures show NIL record on page 4."""
    cand_x_conv = db_session.execute(
        select(Disclosure).where(
            Disclosure.affidavit_id == 1,
            Disclosure.category == "convictions",
        )
    ).scalar_one()
    assert cand_x_conv.structured_value == {"count": 0, "status": "NIL"}
    assert cand_x_conv.page_number == 4
    assert cand_x_conv.verification_status == "verified"

    cand_y_conv = db_session.execute(
        select(Disclosure).where(
            Disclosure.affidavit_id == 2,
            Disclosure.category == "convictions",
        )
    ).scalar_one()
    assert cand_y_conv.structured_value == {"count": 0, "status": "NIL"}
    assert cand_y_conv.page_number == 4
    assert cand_y_conv.verification_status == "verified"


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


def test_public_activity_records_and_explanations(db_session):
    """Verify Candidate public activity records, verification statuses, and explanations."""
    all_records = db_session.execute(select(PublicActivityRecord)).scalars().all()
    assert len(all_records) == 6

    # Breakdown by candidate
    cand_x_recs = [r for r in all_records if r.candidate_id == 1]
    cand_y_recs = [r for r in all_records if r.candidate_id == 2]
    cand_z_recs = [r for r in all_records if r.candidate_id == 3]

    assert len(cand_x_recs) == 2
    assert all(r.verification_status == "verified" for r in cand_x_recs)

    assert len(cand_y_recs) == 4
    verified_y = [r for r in cand_y_recs if r.verification_status == "verified"]
    unverified_y = [r for r in cand_y_recs if r.verification_status == "needs_review"]
    assert len(verified_y) == 3
    assert len(unverified_y) == 1

    assert len(cand_z_recs) == 0

    # Test deterministic explanation generation for all records
    evaluative_terms = ["good", "bad", "corrupt", "clean", "poor", "high performance", "low performance"]
    for rec in all_records:
        exps = render_public_record_explanations(rec)
        assert "en" in exps and "te" in exps and "hi" in exps
        assert len(exps["en"]) > 20
        assert len(exps["te"]) > 20
        assert len(exps["hi"]) > 20

        en_lower = exps["en"].lower()
        for term in evaluative_terms:
            assert term not in en_lower, f"Found evaluative term '{term}' in explanation: {exps['en']}"

    # Specific content checks
    works_x = next(r for r in cand_x_recs if r.record_type == "constituency_works")
    x_exps = render_public_record_explanations(works_x)
    assert "29 works were completed out of 35" in x_exps["en"]
    assert "₹14.2 crore" in x_exps["en"]
    assert "MoSPI eSakshi (MPLADS/MLALADS)" in x_exps["en"]

    leg_x = next(r for r in cand_x_recs if r.record_type == "legislative_performance")
    x_leg_exps = render_public_record_explanations(leg_x)
    assert "74% session attendance" in x_leg_exps["en"]
    assert "31 questions" in x_leg_exps["en"]
    assert "12 debates" in x_leg_exps["en"]

    delta_y = next(r for r in cand_y_recs if r.record_type == "form26_five_year_delta")
    y_delta_exps = render_public_record_explanations(delta_y)
    assert "₹45 lakh" in y_delta_exps["en"]
    assert "₹68 lakh" in y_delta_exps["en"]
    assert "2019" in y_delta_exps["en"]
    assert "2024" in y_delta_exps["en"]


import json
from pathlib import Path
from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.database import Base
from app.main import app
from app.models import (
    Affidavit,
    Candidate,
    Constituency,
    Disclosure,
    Election,
    LegalGlossary,
    ReviewEvent,
)
import app.api.v1.admin as admin_module

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PDF = WORKSPACE_ROOT / "fixtures" / "fictional" / "candidate_x_affidavit.pdf"


@pytest.fixture
def isolated_pipeline_env(tmp_path, monkeypatch):
    """
    Isolated testing environment:
    - Temporary SQLite DB in tmp_path (never mutates apps/api/nagrik_lens.db)
    - Temporary uploads directory in tmp_path (never writes to workspace uploads/)
    - FastApi dependency_overrides[get_db] connected to isolated DB
    """
    # 1. Point WORKSPACE_ROOT in admin module to tmp_path
    monkeypatch.setattr(admin_module, "WORKSPACE_ROOT", tmp_path)

    # 2. Setup isolated SQLite DB
    test_db_path = tmp_path / "test_pipeline.db"
    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # 3. Seed isolated database with minimal baseline
    db = TestSessionLocal()
    try:
        # Glossary
        glossary_file = WORKSPACE_ROOT / "data" / "glossary" / "legal_terms.json"
        with open(glossary_file, "r", encoding="utf-8") as f:
            glossary_data = json.load(f)
        for g in glossary_data:
            db.add(
                LegalGlossary(
                    code_key=g["code_key"],
                    act_name=g["act_name"],
                    term_en=g["term_en"],
                    explanation_en=g["explanation_en"],
                    explanation_te=g["explanation_te"],
                    explanation_hi=g["explanation_hi"],
                    review_status=g.get("review_status", "verified"),
                )
            )

        # Election & Constituency
        election = Election(
            name="Telangana Legislative Assembly General Election 2024 (Fictional Sample)",
            election_type="Assembly",
            year=2024,
            state="Telangana",
        )
        db.add(election)
        db.flush()

        constituency = Constituency(
            election_id=election.id,
            name="Fictional Constituency",
            code="FC-01",
            state="Telangana",
        )
        db.add(constituency)
        db.flush()

        # Candidate
        candidate = Candidate(
            constituency_id=constituency.id,
            name="Candidate X",
            display_name="Candidate X (Fictional Sample)",
            party_name="Independent — Fictional",
            is_fictional=True,
        )
        db.add(candidate)
        db.commit()
    finally:
        db.close()

    # 4. FastAPI dependency override
    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    yield client, TestSessionLocal, tmp_path

    app.dependency_overrides.clear()


def test_upload_non_pdf_file_rejected(isolated_pipeline_env):
    """Test 1: Uploading a non-PDF file returns HTTP 400 and validation error."""
    client, _, _ = isolated_pipeline_env

    # Text bytes without %PDF magic header
    fake_content = b"This is an arbitrary text file and not a PDF document."
    response = client.post(
        "/api/v1/admin/affidavits/upload",
        headers={"X-Admin-Key": "dev-secret-key"},
        data={"candidate_id": 1, "filing_date": "2024-04-15"},
        files={"file": ("malicious.txt", fake_content, "application/pdf")},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "PDF validation failed" in detail
    assert "missing '%pdf' header" in detail.lower()


def test_upload_valid_form26_pdf(isolated_pipeline_env):
    """Test 2: Uploading candidate_x_affidavit.pdf succeeds (HTTP 201), returns 4 pages and valid SHA-256."""
    client, SessionLocal, tmp_path = isolated_pipeline_env

    assert FIXTURE_PDF.exists(), f"Fixture PDF missing at {FIXTURE_PDF}"
    pdf_bytes = FIXTURE_PDF.read_bytes()

    response = client.post(
        "/api/v1/admin/affidavits/upload",
        headers={"X-Admin-Key": "dev-secret-key"},
        data={
            "candidate_id": 1,
            "filing_date": "2024-04-15",
            "source_url": "https://eci.gov.in/fictional/candidate_x_form26.pdf",
        },
        files={"file": ("candidate_x_affidavit.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()

    # Verify inspection report
    inspection = payload["inspection"]
    assert inspection["page_count"] == 4
    assert inspection["file_hash"] == "0221bbfe015d400c1b80f3686a5a8fb1407942b01569e2e047a96852add05504"
    assert inspection["digital_pages"] == 4
    assert inspection["scanned_pages"] == 0
    assert len(inspection["page_diagnostics"]) == 4

    # Verify affidavit metadata
    affidavit = payload["affidavit"]
    assert affidavit["id"] == 1
    assert affidavit["candidate_id"] == 1
    assert affidavit["processing_status"] == "uploaded"
    assert affidavit["publication_status"] == "draft"

    # Verify file is stored in isolated tmp_path/uploads/affidavits/
    db = SessionLocal()
    try:
        aff_db = db.execute(select(Affidavit).where(Affidavit.id == 1)).scalar_one()
        stored_file = tmp_path / aff_db.file_path
        assert stored_file.exists()
        assert stored_file.is_file()
        assert len(stored_file.read_bytes()) == len(pdf_bytes)
    finally:
        db.close()


def test_extract_affidavit_creates_needs_review_disclosures(isolated_pipeline_env):
    """Test 3: POST /api/v1/admin/affidavits/{id}/extract creates draft disclosures marked 'needs_review'."""
    client, SessionLocal, _ = isolated_pipeline_env

    # 1. Upload the PDF first
    pdf_bytes = FIXTURE_PDF.read_bytes()
    upload_res = client.post(
        "/api/v1/admin/affidavits/upload",
        headers={"X-Admin-Key": "dev-secret-key"},
        data={"candidate_id": 1, "filing_date": "2024-04-15"},
        files={"file": ("candidate_x_affidavit.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload_res.status_code == 201
    affidavit_id = upload_res.json()["affidavit"]["id"]

    # 2. Run extraction
    extract_res = client.post(
        f"/api/v1/admin/affidavits/{affidavit_id}/extract",
        headers={"X-Admin-Key": "dev-secret-key"},
    )
    assert extract_res.status_code == 200
    extract_data = extract_res.json()

    assert extract_data["affidavit_id"] == affidavit_id
    assert extract_data["processing_status"] == "extracted"
    assert extract_data["pages_inspected"] == 4
    assert extract_data["disclosures_extracted"] == 7
    assert len(extract_data["warnings"]) == 0

    # 3. Verify in database: ALL disclosures MUST be needs_review
    db = SessionLocal()
    try:
        disclosures = db.execute(
            select(Disclosure).where(Disclosure.affidavit_id == affidavit_id)
        ).scalars().all()

        assert len(disclosures) == 7

        page_mapping = {}
        for d in disclosures:
            assert d.verification_status == "needs_review", (
                f"CRITICAL TRUST VIOLATION: Extracted disclosure {d.category}:{d.field_key} "
                f"has status '{d.verification_status}', must be 'needs_review'"
            )
            page_mapping[(d.category, d.subject_type)] = d.page_number

        # Verify accurate page number mapping
        assert page_mapping[("education", "self")] == 1
        assert page_mapping[("movable_assets", "self")] == 2
        assert page_mapping[("movable_assets", "spouse")] == 2
        assert page_mapping[("immovable_assets", "self")] == 2
        assert page_mapping[("liabilities", "self")] == 3
        assert page_mapping[("pending_criminal_cases", "self")] == 4
        assert page_mapping[("convictions", "self")] == 4

        # Verify review audit events logged
        events = db.execute(
            select(ReviewEvent)
            .join(Disclosure, ReviewEvent.disclosure_id == Disclosure.id)
            .where(Disclosure.affidavit_id == affidavit_id)
        ).scalars().all()

        assert len(events) == 7
        for ev in events:
            assert ev.reviewer_name == "Automated PDF Extractor"
            assert ev.action == "auto_extracted"
            assert ev.new_value.get("verification_status") == "needs_review"
    finally:
        db.close()


def test_public_endpoint_empty_before_human_verification(isolated_pipeline_env):
    """Test 4: Public GET /api/v1/affidavits/{id}/disclosures returns [] for extracted but unverified affidavit."""
    client, _, _ = isolated_pipeline_env

    # 1. Upload and extract
    pdf_bytes = FIXTURE_PDF.read_bytes()
    upload_res = client.post(
        "/api/v1/admin/affidavits/upload",
        headers={"X-Admin-Key": "dev-secret-key"},
        data={"candidate_id": 1, "filing_date": "2024-04-15"},
        files={"file": ("candidate_x_affidavit.pdf", pdf_bytes, "application/pdf")},
    )
    affidavit_id = upload_res.json()["affidavit"]["id"]

    extract_res = client.post(
        f"/api/v1/admin/affidavits/{affidavit_id}/extract",
        headers={"X-Admin-Key": "dev-secret-key"},
    )
    assert extract_res.status_code == 200

    # 2. Public endpoint MUST return empty list [] because verification_status="needs_review"
    public_res = client.get(f"/api/v1/affidavits/{affidavit_id}/disclosures")
    assert public_res.status_code == 200
    assert public_res.json() == []

    # Check multilingual query parameter also returns empty list
    for lang in ["en", "te", "hi"]:
        res = client.get(f"/api/v1/affidavits/{affidavit_id}/disclosures?lang={lang}")
        assert res.status_code == 200
        assert res.json() == []

    # But admin endpoint CAN see all 7 disclosures
    admin_res = client.get(
        f"/api/v1/admin/affidavits/{affidavit_id}/disclosures",
        headers={"X-Admin-Key": "dev-secret-key"},
    )
    assert admin_res.status_code == 200
    assert len(admin_res.json()) == 7


def test_re_extraction_preserves_human_verified_disclosures(isolated_pipeline_env):
    """Test 5: Re-running extraction NEVER overwrites or downgrades a human-verified disclosure."""
    client, SessionLocal, _ = isolated_pipeline_env

    # 1. Upload and extract
    pdf_bytes = FIXTURE_PDF.read_bytes()
    upload_res = client.post(
        "/api/v1/admin/affidavits/upload",
        headers={"X-Admin-Key": "dev-secret-key"},
        data={"candidate_id": 1},
        files={"file": ("candidate_x_affidavit.pdf", pdf_bytes, "application/pdf")},
    )
    affidavit_id = upload_res.json()["affidavit"]["id"]

    client.post(
        f"/api/v1/admin/affidavits/{affidavit_id}/extract",
        headers={"X-Admin-Key": "dev-secret-key"},
    )

    # 2. Human reviewer verifies disclosure #1 (Education) and customizes review note
    db = SessionLocal()
    try:
        edu_disc = db.execute(
            select(Disclosure).where(
                Disclosure.affidavit_id == affidavit_id,
                Disclosure.category == "education",
            )
        ).scalar_one()
        edu_id = edu_disc.id
    finally:
        db.close()

    patch_res = client.patch(
        f"/api/v1/admin/disclosures/{edu_id}",
        headers={"X-Admin-Key": "dev-secret-key"},
        json={
            "verification_status": "verified",
            "reviewer_name": "Chief Returning Officer",
            "review_note": "Manually verified against university records.",
            "structured_value": {
                "degree": "Bachelor of Commerce (B.Com) Honours",
                "institution": "Osmania University",
                "year": 2012,
            },
        },
    )
    assert patch_res.status_code == 200

    # Verify public endpoint now surfaces exactly this 1 verified disclosure
    public_res = client.get(f"/api/v1/affidavits/{affidavit_id}/disclosures")
    assert public_res.status_code == 200
    assert len(public_res.json()) == 1
    assert public_res.json()[0]["category"] == "education"

    # 3. Run extraction AGAIN on the same affidavit
    re_extract_res = client.post(
        f"/api/v1/admin/affidavits/{affidavit_id}/extract",
        headers={"X-Admin-Key": "dev-secret-key"},
    )
    assert re_extract_res.status_code == 200

    # 4. Verify human-verified item is completely untouched
    db = SessionLocal()
    try:
        edu_disc_after = db.execute(
            select(Disclosure).where(Disclosure.id == edu_id)
        ).scalar_one()
        assert edu_disc_after.verification_status == "verified"
        assert edu_disc_after.structured_value["degree"] == "Bachelor of Commerce (B.Com) Honours"
    finally:
        db.close()


def test_admin_auth_and_not_found_handling(isolated_pipeline_env):
    """Test 6: Verify admin auth headers and 404 responses for upload and extract."""
    client, _, _ = isolated_pipeline_env
    pdf_bytes = FIXTURE_PDF.read_bytes()

    # Upload without auth header
    res_no_auth = client.post(
        "/api/v1/admin/affidavits/upload",
        data={"candidate_id": 1},
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
    )
    assert res_no_auth.status_code == 401

    # Upload with bad auth header
    res_bad_auth = client.post(
        "/api/v1/admin/affidavits/upload",
        headers={"X-Admin-Key": "wrong-secret"},
        data={"candidate_id": 1},
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
    )
    assert res_bad_auth.status_code == 403

    # Upload for nonexistent candidate
    res_no_cand = client.post(
        "/api/v1/admin/affidavits/upload",
        headers={"X-Admin-Key": "dev-secret-key"},
        data={"candidate_id": 999999},
        files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
    )
    assert res_no_cand.status_code == 404

    # Extract for nonexistent affidavit
    res_no_aff = client.post(
        "/api/v1/admin/affidavits/999999/extract",
        headers={"X-Admin-Key": "dev-secret-key"},
    )
    assert res_no_aff.status_code == 404


def test_parse_indian_amount_normalizer():
    """Test 7: Verify parse_indian_amount normalizes real Form 26 expressions."""
    from app.services.pdf_pipeline.extractor import parse_indian_amount

    test_cases = [
        ("₹5,00,000", 500000),
        ("Rs. 102 Lacs", 10200000),
        ("Rs. 71.50 Lacs", 7150000),
        ("Rs. 23 Lakhs", 2300000),
        ("Rs. 4.80 Cr.", 48000000),
        ("Rs. 1.00 Crores", 10000000),
        ("Rs 1.20 cr", 12000000),
        ("30,000", 30000),
        ("10,000", 10000),
        ("-NA-", 0),
        ("NIL", 0),
        ("N.A.", 0),
        ("Not Applicable", 0),
        (None, None),
        ("Arbitrary text without numbers", None),
    ]

    for raw, expected in test_cases:
        assert parse_indian_amount(raw) == expected, f"Failed parsing: {raw}"


def test_anti_hallucination_empty_dummy_pdf():
    """Test 8: Minimal 1-page dummy PDF must extract 0 disclosures and NEVER hallucinate synthetic values."""
    import pymupdf
    from app.services.pdf_pipeline.extractor import extract_affidavit_disclosures_from_bytes

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello world — empty test document")
    pdf_bytes = doc.tobytes()
    doc.close()

    result = extract_affidavit_disclosures_from_bytes(pdf_bytes)

    # Must extract 0 disclosures
    assert len(result.disclosures) == 0, f"Expected 0 disclosures, got {len(result.disclosures)}"

    # Must NEVER contain synthetic candidate placeholders
    result_str = str(result.to_dict())
    forbidden_defaults = [
        "112/2022",
        "Fictional PS",
        "IPC 143",
        "2012",
        "Regular Undergraduate Degree Program",
        "CC/450/2023",
        "Judicial First Class Magistrate Court",
        "Public Sector Bank (Fictional National Bank, Main Branch)",
    ]
    for forbidden in forbidden_defaults:
        assert forbidden not in result_str, f"CRITICAL ANTI-HALLUCINATION FAILURE: Found '{forbidden}'"


def test_part_a_vs_part_b_mismatch_warning():
    """Test 9: Discrepancy between Part-A table and Part-B abstract emits [PART-A vs PART-B MISMATCH]."""
    import pymupdf
    from app.services.pdf_pipeline.extractor import extract_affidavit_disclosures_from_bytes

    doc = pymupdf.open()
    # Page 1: Part-A
    p1 = doc.new_page()
    p1.insert_text((50, 50), """
ITEM (7) DETAILS OF MOVABLE ASSETS
Gross Total Movable Assets
Rs. 102 Lacs
Nil
""")
    # Page 2: Part-B
    p2 = doc.new_page()
    p2.insert_text((50, 50), """
PART-B
ABSTRACT OF THE DETAILS GIVEN IN (1) TO (10) OF PART-A
8. Details of Assets and Liabilities in Rupees:
(A) Moveable Assets (Total Value)
Rs. 102 Cr.
Nil
""")
    pdf_bytes = doc.tobytes()
    doc.close()

    result = extract_affidavit_disclosures_from_bytes(pdf_bytes)
    mismatch_warnings = [w for w in result.warnings if "[PART-A vs PART-B MISMATCH]" in w]
    assert len(mismatch_warnings) >= 1

    warning_text = mismatch_warnings[0]
    assert "page 1" in warning_text.lower()
    assert "page 2" in warning_text.lower()
    assert "₹1,02,00,000" in warning_text
    assert "₹1,02,00,00,000" in warning_text


def test_real_eci_education_strips_boilerplate():
    """Test 10: Standard ECI instruction boilerplate is filtered, extracting real declared degree."""
    import pymupdf
    from app.services.pdf_pipeline.extractor import extract_affidavit_disclosures_from_bytes

    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text((50, 50), """
ADVOCATE & NOTARY
APPOINTED BY GOVT. OF TELANGANA
Regd. No. 1234/2018, GOMs No. 567
(10) My educational qualification is as under:
(Give details of highest School/University education mentioning the full form of the certificate/diploma/degree course, name of the School/College/University and the year in which the course was completed.)
M.A., LL.B, OSMANIA UNIVERSITY, 1998
""")
    pdf_bytes = doc.tobytes()
    doc.close()

    result = extract_affidavit_disclosures_from_bytes(pdf_bytes)
    assert len(result.disclosures) == 1
    edu = result.disclosures[0]

    assert edu.category == "education"
    assert "give details" not in edu.structured_value["degree"].lower()
    assert "certificate" not in edu.structured_value["degree"].lower()
    assert edu.structured_value["degree"] == "M.A., LL.B"
    assert edu.structured_value["institution"] == "OSMANIA UNIVERSITY"
    assert edu.structured_value["year"] == 1998


def test_legal_sections_extractor_supports_multiple_acts():
    """Test 11: Legal section extractor parses IPC, BNS, and Special Acts (e.g. MCOC Act)."""
    from app.services.pdf_pipeline.extractor import extract_legal_sections

    s1 = extract_legal_sections("120(B) IPC, Sec. 3(2) 24 of MCOC Act")
    assert any("MCOC Act" in s for s in s1)
    assert any("120(B) IPC" in s for s in s1)

    s2 = extract_legal_sections("Sections: BNS 103, BNS 115")
    assert "BNS 103" in s2
    assert "BNS 115" in s2

    s3 = extract_legal_sections("Section 302 of IPC, Section 25 Arms Act")
    assert any("Arms Act" in s for s in s3)
    assert any("IPC" in s for s in s3)

    s4 = extract_legal_sections("Plain statement with no criminal sections")
    assert s4 == []


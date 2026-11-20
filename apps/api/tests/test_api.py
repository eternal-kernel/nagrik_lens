import json
from pathlib import Path
from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
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

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def isolated_test_client(tmp_path_factory):
    """Fixture providing a TestClient wired to an isolated temporary SQLite database."""
    tmp_dir = tmp_path_factory.mktemp("nagrik_test_db")
    test_db_path = tmp_dir / "isolated_nagrik_lens.db"
    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create tables
    Base.metadata.create_all(bind=test_engine)

    # Seed isolated database with exact fictional fixtures
    db = TestSessionLocal()
    try:
        # 1. Glossary
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

        # 2. Election
        election = Election(
            name="Telangana Legislative Assembly General Election 2024 (Fictional Sample)",
            election_type="Assembly",
            year=2024,
            state="Telangana",
        )
        db.add(election)
        db.flush()

        # 3. Constituency
        constituency = Constituency(
            election_id=election.id,
            name="Fictional Constituency",
            code="FC-01",
            state="Telangana",
        )
        db.add(constituency)
        db.flush()

        # 4. Candidate
        candidate = Candidate(
            constituency_id=constituency.id,
            name="Candidate X",
            display_name="Candidate X (Fictional Sample)",
            party_name="Independent — Fictional",
            is_fictional=True,
        )
        db.add(candidate)
        db.flush()

        # 5. Affidavit
        affidavit = Affidavit(
            candidate_id=candidate.id,
            source_url="https://eci.gov.in/fictional/candidate_x_form26.pdf",
            file_path="fixtures/fictional/candidate_x_affidavit.pdf",
            file_hash="0221bbfe015d400c1b80f3686a5a8fb1407942b01569e2e047a96852add05504",
            filing_date=date(2024, 4, 15),
            processing_status="processed",
            publication_status="pending_review",
            redaction_boxes=None,
        )
        db.add(affidavit)
        db.flush()

        # 6. Disclosures (6 verified, 1 needs_review)
        disclosures_data = [
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
                "raw_excerpt": "B.Com, Osmania University, 2012",
            },
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
                },
                "raw_excerpt": "Self Movable Assets: ₹5,00,000",
            },
            {
                "category": "movable_assets",
                "field_key": "gross_total_movable_assets",
                "subject_type": "spouse",
                "page_number": 2,
                "verification_status": "needs_review",  # Gate item
                "structured_value": {
                    "currency": "INR",
                    "amount": 320000,
                    "formatted": "₹3,20,000",
                },
                "raw_excerpt": "Spouse Movable Assets: ₹3,20,000",
            },
            {
                "category": "immovable_assets",
                "field_key": "agricultural_land_current_market_value",
                "subject_type": "self",
                "page_number": 2,
                "verification_status": "verified",
                "structured_value": {
                    "asset_type": "Agricultural land",
                    "currency": "INR",
                    "amount": 1800000,
                    "formatted": "₹18,00,000",
                },
                "raw_excerpt": "Self Immovable Assets: Agricultural land valued at ₹18,00,000",
            },
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
                },
                "raw_excerpt": "Home loan from Public Sector Bank: ₹6,50,000; Government Dues: Nil",
            },
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
                "raw_excerpt": "FIR No. 112/2022, Fictional PS; Case No. CC/450/2023...",
            },
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
            },
        ]

        for d in disclosures_data:
            disc = Disclosure(
                affidavit_id=affidavit.id,
                category=d["category"],
                field_key=d["field_key"],
                subject_type=d["subject_type"],
                page_number=d["page_number"],
                verification_status=d["verification_status"],
                structured_value=d["structured_value"],
                raw_excerpt=d["raw_excerpt"],
            )
            db.add(disc)
            db.flush()

            # Add initial review event
            db.add(
                ReviewEvent(
                    disclosure_id=disc.id,
                    reviewer_name="Audit Lead (Test)",
                    action="verified" if d["verification_status"] == "verified" else "flagged",
                    previous_value=None,
                    new_value={"verification_status": d["verification_status"]},
                    review_note="Initial test event",
                    created_at=datetime.now(timezone.utc),
                )
            )

        db.commit()
    finally:
        db.close()

    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_health_check(isolated_test_client):
    """GET /api/v1/health returns 200 with service info."""
    resp = isolated_test_client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "nagrik-lens-api"
    assert data["version"] == "0.1.0"


def test_get_elections(isolated_test_client):
    """GET /api/v1/elections returns elections with nested constituencies."""
    resp = isolated_test_client.get("/api/v1/elections")
    assert resp.status_code == 200
    elections = resp.json()
    assert len(elections) == 1
    assert elections[0]["state"] == "Telangana"
    assert len(elections[0]["constituencies"]) == 1
    assert elections[0]["constituencies"][0]["code"] == "FC-01"


def test_get_candidates(isolated_test_client):
    """GET /api/v1/candidates returns candidates with election/constituency context."""
    resp = isolated_test_client.get("/api/v1/candidates")
    assert resp.status_code == 200
    candidates = resp.json()
    assert len(candidates) == 1
    c = candidates[0]
    assert c["name"] == "Candidate X"
    assert c["display_name"] == "Candidate X (Fictional Sample)"
    assert c["is_fictional"] is True
    assert c["constituency_name"] == "Fictional Constituency"

    # Search filter test
    resp_found = isolated_test_client.get("/api/v1/candidates?search=Candidate")
    assert resp_found.status_code == 200
    assert len(resp_found.json()) == 1

    resp_empty = isolated_test_client.get("/api/v1/candidates?search=NonExistent")
    assert resp_empty.status_code == 200
    assert len(resp_empty.json()) == 0


def test_get_candidate_detail(isolated_test_client):
    """GET /api/v1/candidates/{id} returns candidate detail with affidavits."""
    resp = isolated_test_client.get("/api/v1/candidates/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Candidate X"
    assert data["constituency"]["code"] == "FC-01"
    assert data["election"]["name"].startswith("Telangana Legislative Assembly")
    assert len(data["affidavits"]) == 1
    aff = data["affidavits"][0]
    assert aff["filing_date"] == "2024-04-15"
    assert "0221bbfe" in aff["file_hash"]


def test_public_disclosures_guardrail(isolated_test_client):
    """STRICT GUARDRAIL: Public disclosures MUST return ONLY verified disclosures.

    Must return exactly 6 verified disclosures and strictly exclude movable_assets_spouse (needs_review).
    """
    resp = isolated_test_client.get("/api/v1/affidavits/1/disclosures?lang=en")
    assert resp.status_code == 200
    disclosures = resp.json()
    assert len(disclosures) == 6

    # Verify every returned disclosure is strictly verified
    for d in disclosures:
        assert d["verification_status"] == "verified"
        assert "declared by the candidate" in d["explanation"].lower() or "declared by" in d["explanation"].lower()

    # Verify that spouse movable assets (needs_review) is NOT present
    spouse_movable = [
        d for d in disclosures if d["category"] == "movable_assets" and d["subject_type"] == "spouse"
    ]
    assert len(spouse_movable) == 0


def test_public_disclosures_multilingual(isolated_test_client):
    """Verify /disclosures works for lang=en, lang=te, lang=hi, and returns 400 for invalid languages."""
    # English
    resp_en = isolated_test_client.get("/api/v1/affidavits/1/disclosures?lang=en")
    assert resp_en.status_code == 200
    assert "Declared by the candidate" in resp_en.json()[0]["explanation"]

    # Telugu
    resp_te = isolated_test_client.get("/api/v1/affidavits/1/disclosures?lang=te")
    assert resp_te.status_code == 200
    assert "ఫారం 26 అఫిడవిట్" in resp_te.json()[0]["explanation"]

    # Hindi
    resp_hi = isolated_test_client.get("/api/v1/affidavits/1/disclosures?lang=hi")
    assert resp_hi.status_code == 200
    assert "फॉर्म 26 शपथ पत्र" in resp_hi.json()[0]["explanation"]

    # Invalid language -> HTTP 400
    resp_invalid = isolated_test_client.get("/api/v1/affidavits/1/disclosures?lang=fr")
    assert resp_invalid.status_code == 400
    assert "Unsupported language 'fr'" in resp_invalid.json()["detail"]


def test_pending_criminal_cases_glossary_attachment(isolated_test_client):
    """Verify pending_criminal_cases disclosure attaches all 4 glossary items and contains no guilt claim."""
    for lang in ["en", "te", "hi"]:
        resp = isolated_test_client.get(f"/api/v1/affidavits/1/disclosures?lang={lang}")
        assert resp.status_code == 200
        disclosures = resp.json()

        criminal_case = next(d for d in disclosures if d["category"] == "pending_criminal_cases")
        assert criminal_case is not None

        # Check attached glossary items
        glossary_keys = [g["code_key"] for g in criminal_case["glossary_items"]]
        assert "IPC_143" in glossary_keys
        assert "IPC_341" in glossary_keys
        assert "STAGE_COGNIZANCE" in glossary_keys
        assert "CHARGES_NOT_FRAMED" in glossary_keys
        assert len(criminal_case["glossary_items"]) == 4

        # Verify neutral explanation without conviction/guilt claims
        exp = criminal_case["explanation"]
        if lang == "en":
            assert "it is not a conviction" in exp
            assert "guilt has not been established" in exp
        elif lang == "te":
            assert "నేర నిర్ధారణ లేదా శిక్ష ఎంతమాత్రం కాదు" in exp
        elif lang == "hi":
            assert "यह किसी भी प्रकार की दोषसिद्धि (सजा) नहीं है" in exp


def test_affidavit_pdf_streaming(isolated_test_client):
    """GET /api/v1/affidavits/{id}/pdf streams PDF with application/pdf and inline disposition."""
    resp = isolated_test_client.get("/api/v1/affidavits/1/pdf")
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers["content-type"]
    assert "inline" in resp.headers["content-disposition"]
    assert len(resp.content) > 10000  # Non-trivial PDF size


def test_admin_auth_guard(isolated_test_client):
    """Admin routes return 401 when X-Admin-Key is missing, and 403 when wrong."""
    # Missing key -> 401
    resp_no_key = isolated_test_client.get("/api/v1/admin/affidavits/1/disclosures")
    assert resp_no_key.status_code == 401

    # Wrong key -> 403
    resp_wrong_key = isolated_test_client.get(
        "/api/v1/admin/affidavits/1/disclosures",
        headers={"X-Admin-Key": "incorrect-key"},
    )
    assert resp_wrong_key.status_code == 403

    # Valid key -> 200
    resp_valid = isolated_test_client.get(
        "/api/v1/admin/affidavits/1/disclosures",
        headers={"X-Admin-Key": "dev-secret-key"},
    )
    assert resp_valid.status_code == 200
    # Admin view returns ALL 7 disclosures (including needs_review)
    assert len(resp_valid.json()) == 7


def test_get_admin_affidavits_list(isolated_test_client):
    """GET /api/v1/admin/affidavits returns list of candidate affidavits with disclosure breakdown."""
    headers = {"X-Admin-Key": "dev-secret-key"}

    resp = isolated_test_client.get("/api/v1/admin/affidavits", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1

    first_aff = data[0]
    assert first_aff["id"] == 1
    assert first_aff["candidate_id"] == 1
    assert "Candidate X" in first_aff["candidate_name"]
    assert first_aff["disclosure_count"] == 7
    assert first_aff["needs_review_count"] == 1


def test_admin_patch_and_publication_gate(isolated_test_client):
    """Admin PATCH verifying spouse movable assets creates a ReviewEvent and unblocks public endpoint."""
    headers = {"X-Admin-Key": "dev-secret-key"}

    # Find the spouse movable assets disclosure ID (status is needs_review)
    admin_list_resp = isolated_test_client.get(
        "/api/v1/admin/affidavits/1/disclosures", headers=headers
    )
    assert admin_list_resp.status_code == 200
    spouse_disc = next(
        d for d in admin_list_resp.json()
        if d["category"] == "movable_assets" and d["subject_type"] == "spouse"
    )
    disc_id = spouse_disc["id"]
    assert spouse_disc["verification_status"] == "needs_review"
    initial_events_count = len(spouse_disc["review_events"])

    # Admin PATCH to verify the disclosure
    patch_payload = {
        "verification_status": "verified",
        "reviewer_name": "Senior Auditor Jane Doe",
        "review_note": "Spouse bank deposit schedules verified against bank statement.",
    }
    patch_resp = isolated_test_client.patch(
        f"/api/v1/admin/disclosures/{disc_id}",
        json=patch_payload,
        headers=headers,
    )
    assert patch_resp.status_code == 200
    patched_data = patch_resp.json()
    assert patched_data["verification_status"] == "verified"
    assert len(patched_data["review_events"]) == initial_events_count + 1

    latest_event = patched_data["review_events"][-1]
    assert latest_event["reviewer_name"] == "Senior Auditor Jane Doe"
    assert latest_event["action"] == "status_update_to_verified"
    assert latest_event["new_value"]["verification_status"] == "verified"

    # Now verify that public endpoint returns ALL 7 disclosures!
    public_resp = isolated_test_client.get("/api/v1/affidavits/1/disclosures?lang=en")
    assert public_resp.status_code == 200
    public_disclosures = public_resp.json()
    assert len(public_disclosures) == 7

    # And spouse movable assets is now included in public view
    spouse_now_public = next(
        d for d in public_disclosures
        if d["category"] == "movable_assets" and d["subject_type"] == "spouse"
    )
    assert spouse_now_public is not None
    assert spouse_now_public["verification_status"] == "verified"
    assert "₹3.2 lakh" in spouse_now_public["explanation"]


def test_nil_pending_criminal_cases_explanation(isolated_test_client):
    """Regression test: NIL pending criminal cases must render clean NIL text without N/A or glossary items."""
    # Seed Candidate Z with a NIL pending criminal cases disclosure
    db = next(app.dependency_overrides[get_db]())
    try:
        cand_z = Candidate(
            constituency_id=1,
            name="Ananya Sharma",
            display_name="Ananya Sharma (Fictional Sample)",
            party_name="Progressive Alliance — Fictional",
            is_fictional=True,
        )
        db.add(cand_z)
        db.flush()

        affidavit_z = Affidavit(
            candidate_id=cand_z.id,
            source_url="https://eci.gov.in/fictional/candidate_z_form26.pdf",
            file_path="fixtures/fictional/candidate_z_affidavit.pdf",
            file_hash="dummy_hash_z",
            filing_date=date(2024, 4, 17),
            processing_status="processed",
            publication_status="published",
            redaction_boxes=None,
        )
        db.add(affidavit_z)
        db.flush()

        disc_z = Disclosure(
            affidavit_id=affidavit_z.id,
            category="pending_criminal_cases",
            field_key="pending_cases_summary",
            subject_type="self",
            page_number=4,
            verification_status="verified",
            structured_value={"count": 0, "status": "NIL"},
            raw_excerpt="Item (5) Pending Criminal Cases: NIL / NOT APPLICABLE",
        )
        db.add(disc_z)
        db.commit()
        affidavit_z_id = affidavit_z.id
    finally:
        db.close()

    # 1. English
    resp_en = isolated_test_client.get(f"/api/v1/affidavits/{affidavit_z_id}/disclosures?lang=en")
    assert resp_en.status_code == 200
    discs_en = resp_en.json()
    assert len(discs_en) == 1
    d_en = discs_en[0]
    expected_en = "Declared by the candidate in Item (5) of the Form 26 affidavit: no pending criminal cases declared (Pending Criminal Cases: NIL)."
    assert d_en["explanation"] == expected_en
    assert "1 pending criminal case" not in d_en["explanation"]
    assert "N/A" not in d_en["explanation"]
    assert len(d_en["glossary_items"]) == 0

    # 2. Telugu
    resp_te = isolated_test_client.get(f"/api/v1/affidavits/{affidavit_z_id}/disclosures?lang=te")
    assert resp_te.status_code == 200
    discs_te = resp_te.json()
    assert len(discs_te) == 1
    d_te = discs_te[0]
    expected_te = "ఫారం 26 అఫిడవిట్లోని ఐటెమ్ (5) లో అభ్యర్థి ప్రకటించిన వివరాల ప్రకారం: ఎలాంటి క్రిమినల్ కేసులు పెండింగ్లో లేవు (పెండింగ్ క్రిమినల్ కేసులు: ఏమీ లేవు / NIL)."
    assert d_te["explanation"] == expected_te
    assert "1 క్రిమినల్ కేసు" not in d_te["explanation"]
    assert "N/A" not in d_te["explanation"]
    assert len(d_te["glossary_items"]) == 0

    # 3. Hindi
    resp_hi = isolated_test_client.get(f"/api/v1/affidavits/{affidavit_z_id}/disclosures?lang=hi")
    assert resp_hi.status_code == 200
    discs_hi = resp_hi.json()
    assert len(discs_hi) == 1
    d_hi = discs_hi[0]
    expected_hi = "फॉर्म 26 शपथ पत्र के मद (5) में उम्मीदवार द्वारा घोषित विवरण के अनुसार: कोई भी आपराधिक मामला लंबित नहीं है (लंबित आपराधिक मामले: शून्य / NIL)।"
    assert d_hi["explanation"] == expected_hi
    assert "1 आपराधिक मामला" not in d_hi["explanation"]
    assert "N/A" not in d_hi["explanation"]
    assert len(d_hi["glossary_items"]) == 0

    # Also verify Candidate X convictions wording in English is tightened
    resp_conv = isolated_test_client.get("/api/v1/affidavits/1/disclosures?lang=en")
    assert resp_conv.status_code == 200
    conv_disc = next(d for d in resp_conv.json() if d["category"] == "convictions")
    assert conv_disc["explanation"] == "Declared by the candidate in Item (6) of the Form 26 affidavit: no criminal convictions declared (Convictions: NIL)."

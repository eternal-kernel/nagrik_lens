from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from scripts.seed_fictional import seed_database

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = WORKSPACE_ROOT / "fixtures" / "fictional"

EVALUATIVE_TERMS = [
    "good", "bad", "poor", "corrupt", "clean", "active", "inactive",
    "high performance", "low performance", "excellent", "terrible",
]


@pytest.fixture(scope="module")
def client():
    """Ensure seeded fictional database is initialized and return TestClient."""
    seed_database()
    with TestClient(app) as test_client:
        yield test_client


def test_candidate_kiran_rao_verified_public_records_guardrail(client):
    """Verify Candidate Y (Kiran Rao) returns prior_office_held, 3 verified public records,
    and strictly omits the unverified 'needs_review' supplementary grant record.
    """
    resp = client.get("/api/v1/candidates/2")
    assert resp.status_code == 200
    data = resp.json()

    # Candidate details & prior office
    assert data["id"] == 2
    assert data["name"] == "Kiran Rao"
    assert data["prior_office_held"] == "MLA — Fictional Constituency (2019–2024)"

    # Hard publication gate: Exactly 3 verified records returned (out of 4 in DB)
    public_records = data["public_records"]
    assert len(public_records) == 3, f"Expected 3 verified records, got {len(public_records)}"

    # All returned records must have verification_status == "verified"
    for rec in public_records:
        assert rec["verification_status"] == "verified"
        assert "needs_review" != rec["verification_status"]
        assert "unverified" not in rec["verification_status"]

        # Check multilingual explanations
        exps = rec["explanations"]
        assert "en" in exps and "te" in exps and "hi" in exps
        assert len(exps["en"]) > 20
        assert len(exps["te"]) > 20
        assert len(exps["hi"]) > 20

        # Assert zero evaluative language in English explanation
        en_lower = exps["en"].lower()
        for term in EVALUATIVE_TERMS:
            assert term not in en_lower, f"Found evaluative word '{term}' in explanation: {exps['en']}"

    # Verify specific record types
    record_types = {r["record_type"] for r in public_records}
    assert record_types == {"constituency_works", "legislative_performance", "form26_five_year_delta"}

    # Verify constituency_works content
    cw_rec = next(r for r in public_records if r["record_type"] == "constituency_works")
    assert cw_rec["structured_payload"]["works_completed"] == 38
    assert cw_rec["structured_payload"]["works_recommended"] == 44
    assert cw_rec["structured_payload"]["funds_utilized"] == 184000000
    assert "38 works were completed out of 44" in cw_rec["explanations"]["en"]

    # Verify legislative_performance content
    lp_rec = next(r for r in public_records if r["record_type"] == "legislative_performance")
    assert lp_rec["structured_payload"]["attendance_percentage"] == 82
    assert lp_rec["structured_payload"]["questions_asked"] == 47
    assert "82% session attendance" in lp_rec["explanations"]["en"]

    # Verify form26_five_year_delta content
    delta_rec = next(r for r in public_records if r["record_type"] == "form26_five_year_delta")
    assert "45 lakh" in delta_rec["explanations"]["en"]
    assert "68 lakh" in delta_rec["explanations"]["en"]


def test_candidate_ananya_sharma_first_time_candidate(client):
    """Verify Candidate Z (Ananya Sharma, first-time contestant) has prior_office_held is None
    and returns an empty public_records array.
    """
    resp = client.get("/api/v1/candidates/3")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == 3
    assert data["name"] == "Ananya Sharma"
    assert data["prior_office_held"] is None
    assert data["public_records"] == []


def test_candidate_x_incumbent_public_records(client):
    """Verify Candidate X (Incumbent) returns prior_office_held and 2 verified public records."""
    resp = client.get("/api/v1/candidates/1")
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == 1
    assert data["prior_office_held"] == "MLA — Fictional Constituency (2019–2024)"
    assert len(data["public_records"]) == 2

    for rec in data["public_records"]:
        assert rec["verification_status"] == "verified"
        en_lower = rec["explanations"]["en"].lower()
        for term in EVALUATIVE_TERMS:
            assert term not in en_lower, f"Found evaluative word '{term}' in explanation: {rec['explanations']['en']}"


def test_poster_scanner_five_year_preview_multi_candidate(client):
    """Verify POST /api/v1/scan on multi-candidate poster fixture attaches accurate
    FiveYearPreview data for both Kiran Rao (incumbent) and Ananya Sharma (first-time).
    """
    poster_path = FIXTURES_DIR / "poster_multi_candidate.png"
    assert poster_path.exists(), f"Poster fixture not found at {poster_path}"

    with open(poster_path, "rb") as f:
        resp = client.post(
            "/api/v1/scan",
            files={"file": ("poster_multi_candidate.png", f, "image/png")},
        )

    assert resp.status_code == 200
    data = resp.json()

    matches = data["matches"]
    assert len(matches) == 2, f"Expected 2 matches, got {len(matches)}"

    # Match by candidate name
    kiran_match = next((m for m in matches if m["name"] == "Kiran Rao"), None)
    ananya_match = next((m for m in matches if m["name"] == "Ananya Sharma"), None)

    assert kiran_match is not None, "Kiran Rao not found in matches"
    assert ananya_match is not None, "Ananya Sharma not found in matches"

    # Kiran Rao five_year_preview verification
    k_preview = kiran_match["five_year_preview"]
    assert k_preview is not None
    assert k_preview["is_incumbent"] is True
    assert k_preview["prior_office_held"] == "MLA — Fictional Constituency (2019–2024)"
    assert k_preview["works_completed"] == 38
    assert k_preview["works_recommended"] == 44
    assert k_preview["attendance_pct"] == 82
    assert k_preview["verified_records_count"] == 3  # Strictly verified records, omitting 1 unverified

    # Ananya Sharma five_year_preview verification
    a_preview = ananya_match["five_year_preview"]
    assert a_preview is not None
    assert a_preview["is_incumbent"] is False
    assert a_preview["prior_office_held"] is None
    assert a_preview["works_completed"] is None
    assert a_preview["works_recommended"] is None
    assert a_preview["attendance_pct"] is None
    assert a_preview["verified_records_count"] == 0


def test_poster_scanner_supports_both_scan_and_poster_scan_routes(client):
    """Verify both /api/v1/scan and /api/v1/poster/scan route identically and return five_year_preview."""
    poster_path = FIXTURES_DIR / "poster_single_candidate.png"
    assert poster_path.exists(), f"Poster fixture not found at {poster_path}"

    for path in ["/api/v1/scan", "/api/v1/poster/scan"]:
        with open(poster_path, "rb") as f:
            resp = client.post(
                path,
                files={"file": ("poster_single_candidate.png", f, "image/png")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["matches"]) == 1
        top = data["matches"][0]
        assert top["name"] == "Kiran Rao"
        assert top["five_year_preview"]["is_incumbent"] is True
        assert top["five_year_preview"]["verified_records_count"] == 3

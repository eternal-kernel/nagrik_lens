import io
from pathlib import Path
from PIL import Image
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.database import Base
from app.main import app
from app.models.election import Candidate, Constituency, Election
from app.services.poster_scanner.matcher import normalize_text, match_candidates_from_ocr

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = WORKSPACE_ROOT / "fixtures" / "fictional"


@pytest.fixture(scope="module")
def isolated_client(tmp_path_factory):
    """Fixture providing a TestClient wired to an isolated temporary SQLite database."""
    tmp_dir = tmp_path_factory.mktemp("nagrik_poster_test_db")
    test_db_path = tmp_dir / "isolated_poster_lens.db"
    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create tables
    Base.metadata.create_all(bind=test_engine)

    # Seed isolated database with 3 fictional candidates
    db = TestSessionLocal()
    try:
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

        # Candidate 1: Candidate X
        cand_x = Candidate(
            constituency_id=constituency.id,
            name="Candidate X",
            display_name="Candidate X (Fictional Sample)",
            party_name="Independent — Fictional",
            is_fictional=True,
        )
        db.add(cand_x)

        # Candidate 2: Kiran Rao
        cand_y = Candidate(
            constituency_id=constituency.id,
            name="Kiran Rao",
            display_name="Kiran Rao (Fictional Sample)",
            party_name="Civic Reform Front — Fictional",
            is_fictional=True,
        )
        db.add(cand_y)

        # Candidate 3: Ananya Sharma
        cand_z = Candidate(
            constituency_id=constituency.id,
            name="Ananya Sharma",
            display_name="Ananya Sharma (Fictional Sample)",
            party_name="Progressive Alliance — Fictional",
            is_fictional=True,
        )
        db.add(cand_z)

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


def test_scan_rejects_non_image_file(isolated_client):
    """Verify endpoint rejects text, PDF, and invalid files with HTTP 400."""
    # 1. Plain text file with fake extension
    resp = isolated_client.post(
        "/api/v1/poster/scan",
        files={"file": ("fake_poster.png", b"Hello, this is just plain text not an image", "image/png")},
    )
    assert resp.status_code == 400
    assert "not a valid or decodable image" in resp.json()["detail"].lower()

    # 2. Unsupported MIME type
    resp = isolated_client.post(
        "/api/v1/poster/scan",
        files={"file": ("doc.pdf", b"%PDF-1.4 dummy pdf bytes", "application/pdf")},
    )
    assert resp.status_code == 400
    assert "unsupported image type" in resp.json()["detail"].lower()

    # 3. Empty file
    resp = isolated_client.post(
        "/api/v1/poster/scan",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_scan_rejects_oversized_file(isolated_client):
    """Verify endpoint rejects images over 10 MB with HTTP 400."""
    fake_huge_bytes = b"0" * (11 * 1024 * 1024)
    resp = isolated_client.post(
        "/api/v1/poster/scan",
        files={"file": ("huge.png", fake_huge_bytes, "image/png")},
    )
    assert resp.status_code == 400
    assert "maximum permitted size" in resp.json()["detail"].lower()


def test_scan_single_candidate_poster(isolated_client):
    """Verify poster_single_candidate.png matches Kiran Rao with high confidence and no disambiguation."""
    poster_path = FIXTURES_DIR / "poster_single_candidate.png"
    assert poster_path.exists(), f"Poster fixture not found at {poster_path}"

    with open(poster_path, "rb") as f:
        resp = isolated_client.post(
            "/api/v1/poster/scan",
            files={"file": ("poster_single_candidate.png", f, "image/png")},
        )

    assert resp.status_code == 200
    data = resp.json()

    # OCR text should contain core keywords
    ocr_text = data["ocr_text"]
    assert "KIRAN RAO" in ocr_text
    assert "Civic Reform Front" in ocr_text

    # Matches
    matches = data["matches"]
    assert len(matches) == 1, f"Expected 1 match, got {len(matches)}: {matches}"

    top_match = matches[0]
    assert top_match["name"] == "Kiran Rao"
    assert top_match["display_name"] == "Kiran Rao (Fictional Sample)"
    assert "Civic Reform Front" in top_match["party_name"]
    assert top_match["constituency_code"] == "FC-01"
    assert top_match["confidence"] >= 0.75

    # Disambiguation flags
    assert data["requires_disambiguation"] is False
    assert "high confidence" in data["message"].lower()
    assert data["detected_constituency"] == "Fictional Constituency"
    assert "Civic Reform Front" in data["detected_party"]


def test_scan_multi_candidate_poster(isolated_client):
    """Verify poster_multi_candidate.png matches both Kiran Rao and Ananya Sharma, requiring disambiguation."""
    poster_path = FIXTURES_DIR / "poster_multi_candidate.png"
    assert poster_path.exists(), f"Poster fixture not found at {poster_path}"

    with open(poster_path, "rb") as f:
        resp = isolated_client.post(
            "/api/v1/poster/scan",
            files={"file": ("poster_multi_candidate.png", f, "image/png")},
        )

    assert resp.status_code == 200
    data = resp.json()

    # OCR text should contain both names and event noise
    ocr_text = data["ocr_text"]
    assert "KIRAN RAO" in ocr_text
    assert "ANANYA SHARMA" in ocr_text

    matches = data["matches"]
    assert len(matches) == 2, f"Expected 2 matches, got {len(matches)}: {matches}"

    matched_names = {m["name"] for m in matches}
    assert matched_names == {"Kiran Rao", "Ananya Sharma"}

    for m in matches:
        assert m["confidence"] >= 0.70
        assert m["constituency_code"] == "FC-01"

    # Multi-candidate requires disambiguation
    assert data["requires_disambiguation"] is True
    assert "multiple candidates" in data["message"].lower()


def test_scan_blank_or_unrelated_image(isolated_client):
    """Verify blank or unrelated image returns 0 matches and 0 false positives."""
    # Create an in-memory blank white PNG
    img = Image.new("RGB", (400, 300), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    resp = isolated_client.post(
        "/api/v1/poster/scan",
        files={"file": ("blank.png", buf.getvalue(), "image/png")},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["matches"] == []
    assert data["requires_disambiguation"] is False
    assert "no" in data["message"].lower()

    # Create an unrelated grocery store receipt image
    img2 = Image.new("RGB", (500, 400), color=(255, 255, 255))
    buf2 = io.BytesIO()
    img2.save(buf2, format="PNG")
    buf2.seek(0)

    resp2 = isolated_client.post(
        "/api/v1/poster/scan",
        files={"file": ("receipt.png", buf2.getvalue(), "image/png")},
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["matches"] == []
    assert data2["requires_disambiguation"] is False


def test_normalize_text_and_honorific_stripping():
    """Verify text normalization correctly removes punctuation, excess spaces, and noise."""
    raw = "Vote for Shri Kiran Rao Garu, MLA Candidate for FC-01!!"
    norm = normalize_text(raw)
    assert "kiran rao" in norm
    assert "!!" not in norm
    assert "," not in norm

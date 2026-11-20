import difflib
import re
from typing import List, Optional, Set, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.election import Candidate, Constituency, Election
from app.schemas.poster import CandidateMatchItem, PosterScanResponse

# Campaign noise words and honorifics commonly found on Indian election posters
NOISE_WORDS = {
    # English
    "vote", "for", "voting", "vote for", "support", "elect", "candidate", "mla", "mp",
    "dr", "adv", "advocate", "shri", "smt", "srimati", "mr", "mrs",
    "grand", "public", "meeting", "youth", "wing", "welcome", "convention", "rally",
    "venue", "date", "time", "ground", "grounds", "office", "central",
    "fictional", "demo", "poster", "not", "a", "real", "campaign", "test", "fixture",
    # Telugu
    "garu", "gariki", "anna", "annaki", "gelipinchandi", "vijayam", "manchi", "nayakudu",
    "yuvasena", "mahasabha", "sammelanam",
    # Hindi
    "ji", "bhai", "zindabad", "chunav", "vijay", "pratyashi", "karyakarta",
}


def normalize_text(text: str) -> str:
    """Lowercase, strip non-alphanumeric symbols (keeping spaces), and collapse whitespace."""
    text = text.lower()
    # Replace non-alphanumeric characters with spaces
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    # Collapse multiple whitespace characters
    return re.sub(r"\s+", " ", text).strip()


def clean_party_name(party_name: str) -> str:
    """Extract core party name by removing common suffixes like '— Fictional'."""
    name = re.sub(r"[\s—\-\–]+fictional.*$", "", party_name, flags=re.IGNORECASE)
    name = re.sub(r"[\s—\-\–]+sample.*$", "", name, flags=re.IGNORECASE)
    return normalize_text(name)


def compute_name_score(candidate_name_norm: str, ocr_norm: str, ocr_tokens: List[str]) -> Tuple[float, Optional[str]]:
    """Compute candidate name similarity against normalized OCR text.

    Returns:
        (score, matched_term) where score is between 0.0 and 1.0.
    """
    cand_tokens = candidate_name_norm.split()
    if not cand_tokens:
        return 0.0, None

    # Identify non-noise distinctive tokens in candidate's name
    distinct_tokens = [t for t in cand_tokens if t not in NOISE_WORDS]
    if not distinct_tokens:
        distinct_tokens = cand_tokens

    # Verify that distinctive tokens actually appear in OCR text (as exact word or close fuzzy match)
    distinct_found = 0
    for dt in distinct_tokens:
        if len(dt) <= 2:
            # Short tokens (initials, letters like 'x') require exact word boundary match
            if re.search(r"\b" + re.escape(dt) + r"\b", ocr_norm):
                distinct_found += 1
        else:
            if re.search(r"\b" + re.escape(dt) + r"\b", ocr_norm):
                distinct_found += 1
            elif any(difflib.SequenceMatcher(None, dt, ot).ratio() >= 0.80 for ot in ocr_tokens if len(ot) >= 3):
                distinct_found += 1

    # Require all distinct tokens for 1-2 token names, or >= 66% for longer names
    required_distinct = len(distinct_tokens) if len(distinct_tokens) <= 2 else int(len(distinct_tokens) * 0.66)
    if distinct_found < required_distinct:
        return 0.0, None

    # 1. Exact phrase / substring match with word boundaries
    pattern = r"\b" + re.escape(candidate_name_norm) + r"\b"
    if re.search(pattern, ocr_norm):
        return 0.85, f"exact_name: {candidate_name_norm}"

    # Also check without word boundary if length >= 6
    if len(candidate_name_norm) >= 6 and candidate_name_norm in ocr_norm:
        return 0.80, f"substring_name: {candidate_name_norm}"

    # 2. Token overlap and sliding window fuzzy match
    k = len(cand_tokens)
    best_score = 0.0
    best_term = None

    if len(ocr_tokens) >= k:
        for i in range(len(ocr_tokens) - k + 1):
            window_tokens = ocr_tokens[i : i + k]
            window_str = " ".join(window_tokens)

            # Sequence matcher ratio
            seq_ratio = difflib.SequenceMatcher(None, candidate_name_norm, window_str).ratio()

            # Token overlap count
            overlap = sum(1 for t in cand_tokens if t in window_tokens)
            token_ratio = overlap / k

            # Combined window score
            if token_ratio == 1.0:
                score = max(0.80, seq_ratio)
            else:
                score = (seq_ratio * 0.6) + (token_ratio * 0.4)

            if score > best_score:
                best_score = score
                best_term = f"window: {window_str} (ratio: {seq_ratio:.2f})"

    # Check candidate tokens presence individually
    total_token_presence = sum(1 for t in cand_tokens if re.search(r"\b" + re.escape(t) + r"\b", ocr_norm))
    cand_token_overlap = total_token_presence / k
    if cand_token_overlap >= 0.75:
        overlap_score = 0.65 * cand_token_overlap
        if overlap_score > best_score:
            best_score = overlap_score
            best_term = f"token_overlap: {total_token_presence}/{k} tokens"

    return best_score, best_term


def match_candidates_from_ocr(
    ocr_text: str,
    db: Session,
    constituency_id: Optional[int] = None,
    min_confidence: float = 0.55,
    high_confidence_threshold: float = 0.75,
) -> PosterScanResponse:
    """Match candidates from database against OCR text extracted from campaign poster.

    Args:
        ocr_text: Raw text extracted from poster.
        db: SQLAlchemy database session.
        constituency_id: Optional constituency ID filter.
        min_confidence: Minimum score to include candidate in matches (default 0.55).
        high_confidence_threshold: Score above which a single match does not require disambiguation (default 0.75).

    Returns:
        PosterScanResponse containing ranked matches and disambiguation status.
    """
    if not ocr_text or not ocr_text.strip():
        return PosterScanResponse(
            ocr_text="",
            matches=[],
            requires_disambiguation=False,
            detected_constituency=None,
            detected_party=None,
            message="No text detected in the provided image.",
        )

    ocr_norm = normalize_text(ocr_text)
    ocr_tokens = ocr_norm.split()

    # Query all candidates with relationships
    stmt = (
        select(Candidate)
        .options(
            selectinload(Candidate.constituency).selectinload(Constituency.election),
        )
    )
    if constituency_id is not None:
        stmt = stmt.where(Candidate.constituency_id == constituency_id)

    candidates = db.execute(stmt).scalars().all()

    matches: List[CandidateMatchItem] = []
    detected_constituencies: Set[str] = set()
    detected_parties: Set[str] = set()

    for cand in candidates:
        matched_terms: List[str] = []
        cand_name_norm = normalize_text(cand.name)

        # 1. Name match score
        name_score, name_term = compute_name_score(cand_name_norm, ocr_norm, ocr_tokens)
        if name_term:
            matched_terms.append(name_term)

        # Gate: If name score is below 0.45, do NOT match candidate based on party/constituency alone
        if name_score < 0.45:
            continue

        # 2. Party Context Boost (+0.10)
        party_boost = 0.0
        core_party = clean_party_name(cand.party_name)
        if core_party and (core_party in ocr_norm or re.search(r"\b" + re.escape(core_party) + r"\b", ocr_norm)):
            party_boost = 0.10
            matched_terms.append(f"party: {cand.party_name}")
            detected_parties.add(cand.party_name)
        else:
            # Check party tokens
            party_tokens = [t for t in core_party.split() if len(t) > 3 and t not in NOISE_WORDS]
            if party_tokens:
                overlap = sum(1 for pt in party_tokens if pt in ocr_norm)
                if overlap / len(party_tokens) >= 0.60:
                    party_boost = 0.08
                    matched_terms.append(f"party_tokens: {overlap}/{len(party_tokens)}")
                    detected_parties.add(cand.party_name)

        # 3. Constituency Context Boost (+0.05)
        const_boost = 0.0
        const = cand.constituency
        if const:
            const_name_norm = normalize_text(const.name)
            const_code_norm = normalize_text(const.code)
            const_code_compact = const_code_norm.replace(" ", "")

            if (const_name_norm in ocr_norm) or (const_code_norm in ocr_norm) or (const_code_compact in ocr_norm):
                const_boost = 0.05
                matched_terms.append(f"constituency: {const.name} ({const.code})")
                detected_constituencies.add(const.name)

        total_confidence = min(1.0, name_score + party_boost + const_boost)
        total_confidence = round(total_confidence, 2)

        if total_confidence >= min_confidence:
            matches.append(
                CandidateMatchItem(
                    candidate_id=cand.id,
                    name=cand.name,
                    display_name=cand.display_name,
                    party_name=cand.party_name,
                    constituency_name=const.name if const else "Unknown",
                    constituency_code=const.code if const else None,
                    election_name=const.election.name if const and const.election else None,
                    confidence=total_confidence,
                    matched_terms=matched_terms,
                )
            )

    # Sort matches descending by confidence, then by candidate_id
    matches.sort(key=lambda m: (-m.confidence, m.candidate_id))

    # Determine disambiguation status
    if len(matches) == 0:
        requires_disambiguation = False
        message = "No matching candidates found in the provided image."
    elif len(matches) == 1:
        if matches[0].confidence >= high_confidence_threshold:
            requires_disambiguation = False
            message = f"Identified candidate '{matches[0].display_name}' with high confidence ({matches[0].confidence:.2f})."
        else:
            requires_disambiguation = True
            message = f"Identified candidate '{matches[0].display_name}' with moderate confidence ({matches[0].confidence:.2f}); verification recommended."
    else:
        requires_disambiguation = True
        message = f"Multiple candidates ({len(matches)}) detected; please select the intended candidate."

    return PosterScanResponse(
        ocr_text=ocr_text,
        matches=matches,
        requires_disambiguation=requires_disambiguation,
        detected_constituency=", ".join(sorted(detected_constituencies)) if detected_constituencies else None,
        detected_party=", ".join(sorted(detected_parties)) if detected_parties else None,
        message=message,
    )

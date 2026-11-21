from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.models.election import Candidate, Constituency, Election
from app.schemas.candidate import CandidateDetail, CandidateSummary
from app.schemas.election import ConstituencyRead, ElectionRead
from app.schemas.public_record import PublicActivityRecordOut
from app.services.public_records import (
    get_verified_public_records,
    render_public_record_explanations,
)

router = APIRouter(tags=["Candidates"])


@router.get("/candidates", response_model=List[CandidateSummary])
def get_candidates(
    election_id: Optional[int] = Query(None, description="Filter by election ID"),
    constituency_id: Optional[int] = Query(None, description="Filter by constituency ID"),
    search: Optional[str] = Query(None, description="Search by name or party"),
    db: Session = Depends(get_db),
):
    """List candidates with optional filtering and search."""
    stmt = (
        select(Candidate, Constituency.name, Election.name)
        .join(Constituency, Candidate.constituency_id == Constituency.id)
        .join(Election, Constituency.election_id == Election.id)
    )

    if constituency_id is not None:
        stmt = stmt.where(Candidate.constituency_id == constituency_id)

    if election_id is not None:
        stmt = stmt.where(Constituency.election_id == election_id)

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Candidate.name.ilike(search_pattern),
                Candidate.display_name.ilike(search_pattern),
                Candidate.party_name.ilike(search_pattern),
            )
        )

    stmt = stmt.order_by(Candidate.display_name)
    results = db.execute(stmt).all()

    summaries: List[CandidateSummary] = []
    for cand, const_name, elec_name in results:
        summaries.append(
            CandidateSummary(
                id=cand.id,
                constituency_id=cand.constituency_id,
                name=cand.name,
                display_name=cand.display_name,
                party_name=cand.party_name,
                is_fictional=cand.is_fictional,
                prior_office_held=cand.prior_office_held,
                created_at=cand.created_at,
                constituency_name=const_name,
                election_name=elec_name,
            )
        )
    return summaries


@router.get("/candidates/{candidate_id}", response_model=CandidateDetail)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Get full details for a candidate including election, constituency, affidavits, and verified 5-year public records."""
    stmt = (
        select(Candidate)
        .options(
            selectinload(Candidate.constituency).selectinload(Constituency.election),
            selectinload(Candidate.affidavits),
        )
        .where(Candidate.id == candidate_id)
    )
    candidate = db.execute(stmt).scalar_one_or_none()

    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with ID {candidate_id} not found",
        )

    constituency_read = ConstituencyRead.model_validate(candidate.constituency)
    election_read = (
        ElectionRead.model_validate(candidate.constituency.election)
        if candidate.constituency and candidate.constituency.election
        else None
    )

    # Hard publication gate: Query PublicActivityRecord strictly filtered by verification_status == "verified"
    verified_records = get_verified_public_records(candidate.id, db)
    public_records_out = [
        PublicActivityRecordOut(
            id=rec.id,
            record_type=rec.record_type,
            period_label=rec.period_label,
            source_name=rec.source_name,
            source_url=rec.source_url,
            structured_payload=rec.structured_payload or {},
            explanations=render_public_record_explanations(rec),
            verification_status=rec.verification_status,
        )
        for rec in verified_records
    ]

    return CandidateDetail(
        id=candidate.id,
        constituency_id=candidate.constituency_id,
        name=candidate.name,
        display_name=candidate.display_name,
        party_name=candidate.party_name,
        is_fictional=candidate.is_fictional,
        prior_office_held=candidate.prior_office_held,
        created_at=candidate.created_at,
        constituency=constituency_read,
        election=election_read,
        affidavits=candidate.affidavits,
        public_records=public_records_out,
    )

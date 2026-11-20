from datetime import date, datetime, timezone
from pathlib import Path
import re
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db, verify_admin_key
from app.models.affidavit import Affidavit, Disclosure, ReviewEvent
from app.models.election import Candidate
from app.models.glossary import LegalGlossary
from app.schemas.affidavit import (
    AffidavitExtractionResponse,
    AffidavitSummary,
    AffidavitUploadResponse,
)
from app.schemas.disclosure import (
    AdminDisclosureRead,
    DisclosurePatchRequest,
    ReviewEventRead,
)
from app.services.explanations import build_explanation
from app.services.pdf_pipeline import (
    extract_affidavit_disclosures,
    inspect_pdf_content,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_admin_key)],
)


def get_workspace_root() -> Path:
    """Find the workspace root containing 'fixtures' and 'apps'."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "fixtures").exists() and (parent / "apps").exists():
            return parent
    return current.parents[4].parent


WORKSPACE_ROOT = get_workspace_root()


@router.post(
    "/affidavits/upload",
    response_model=AffidavitUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_affidavit_admin(
    file: UploadFile = File(..., description="ECI Form 26 PDF document"),
    candidate_id: int = Form(..., description="ID of candidate filing this affidavit"),
    filing_date: Optional[str] = Form(None, description="Filing date in YYYY-MM-DD format"),
    source_url: Optional[str] = Form(None, description="Original source or ECI URL"),
    db: Session = Depends(get_db),
):
    """Upload and validate an ECI Form 26 PDF, storing it locally in uploads/affidavits/."""
    # 1. Verify candidate exists
    candidate = db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    ).scalar_one_or_none()
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with ID {candidate_id} not found",
        )

    # 2. Parse filing date
    if filing_date:
        try:
            parsed_date = date.fromisoformat(filing_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filing_date format. Expected YYYY-MM-DD.",
            )
    else:
        parsed_date = date.today()

    # 3. Read and validate PDF content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {e}",
        )

    try:
        inspection = inspect_pdf_content(content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PDF validation failed: {e}",
        )

    # 4. Save to uploads/affidavits/<hash_prefix>_<filename>.pdf
    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", file.filename or "affidavit.pdf")
    stored_name = f"{inspection.file_hash[:12]}_{safe_name}"
    uploads_dir = WORKSPACE_ROOT / "uploads" / "affidavits"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    destination_path = uploads_dir / stored_name

    with open(destination_path, "wb") as f:
        f.write(content)

    relative_path = f"uploads/affidavits/{stored_name}"

    # 5. Create Affidavit DB record
    affidavit = Affidavit(
        candidate_id=candidate_id,
        source_url=source_url,
        file_path=relative_path,
        file_hash=inspection.file_hash,
        filing_date=parsed_date,
        processing_status="uploaded",
        publication_status="draft",
        redaction_boxes=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(affidavit)
    db.commit()
    db.refresh(affidavit)

    return AffidavitUploadResponse(
        affidavit=AffidavitSummary.model_validate(affidavit),
        inspection=inspection.to_dict(),
    )


@router.post(
    "/affidavits/{affidavit_id}/extract",
    response_model=AffidavitExtractionResponse,
)
def extract_affidavit_admin(
    affidavit_id: int,
    db: Session = Depends(get_db),
):
    """Run deterministic extraction on an affidavit PDF, generating draft disclosures marked 'needs_review'."""
    affidavit = db.execute(
        select(Affidavit).where(Affidavit.id == affidavit_id)
    ).scalar_one_or_none()
    if affidavit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Affidavit with ID {affidavit_id} not found",
        )

    raw_path = Path(affidavit.file_path)
    full_path = raw_path if raw_path.is_absolute() else (WORKSPACE_ROOT / raw_path)

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Affidavit PDF file not found on disk at: {affidavit.file_path}",
        )

    try:
        result = extract_affidavit_disclosures(full_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction pipeline failed: {e}",
        )

    # Insert or update draft disclosures
    now_utc = datetime.now(timezone.utc)
    for item in result.disclosures:
        existing = db.execute(
            select(Disclosure).where(
                Disclosure.affidavit_id == affidavit.id,
                Disclosure.category == item.category,
                Disclosure.field_key == item.field_key,
                Disclosure.subject_type == item.subject_type,
            )
        ).scalar_one_or_none()

        if existing is not None:
            # CRITICAL TRUST RULE: Never overwrite a disclosure already approved by human reviewer
            if existing.verification_status == "verified":
                continue
            existing.structured_value = item.structured_value
            existing.raw_excerpt = item.raw_excerpt
            existing.page_number = item.page_number
            existing.updated_at = now_utc
        else:
            new_disc = Disclosure(
                affidavit_id=affidavit.id,
                category=item.category,
                field_key=item.field_key,
                subject_type=item.subject_type,
                structured_value=item.structured_value,
                raw_excerpt=item.raw_excerpt,
                page_number=item.page_number,
                verification_status="needs_review",  # CRITICAL: Always needs_review
                created_at=now_utc,
                updated_at=now_utc,
            )
            db.add(new_disc)
            db.flush()

            # Record automated extraction review event
            db.add(
                ReviewEvent(
                    disclosure_id=new_disc.id,
                    reviewer_name="Automated PDF Extractor",
                    action="auto_extracted",
                    previous_value=None,
                    new_value={
                        "verification_status": "needs_review",
                        "confidence": item.confidence_note,
                    },
                    review_note=f"Extracted via deterministic Form 26 pipeline ({item.confidence_note})",
                    created_at=now_utc,
                )
            )

    affidavit.processing_status = (
        "extracted_with_warnings" if result.warnings else "extracted"
    )
    db.commit()

    return AffidavitExtractionResponse(
        affidavit_id=affidavit.id,
        processing_status=affidavit.processing_status,
        pages_inspected=result.inspection.page_count,
        ocr_pages_detected=result.inspection.scanned_pages,
        disclosures_extracted=len(result.disclosures),
        warnings=result.warnings,
    )


@router.get(
    "/affidavits/{affidavit_id}/disclosures",
    response_model=List[AdminDisclosureRead],
)
def get_all_affidavit_disclosures_admin(
    affidavit_id: int,
    lang: str = Query("en", description="Language code: en, te, or hi"),
    db: Session = Depends(get_db),
):
    """Admin view: Retrieve ALL disclosures for an affidavit with audit history."""
    affidavit = db.execute(
        select(Affidavit).where(Affidavit.id == affidavit_id)
    ).scalar_one_or_none()

    if affidavit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Affidavit with ID {affidavit_id} not found",
        )

    stmt = (
        select(Disclosure)
        .options(selectinload(Disclosure.review_events))
        .where(Disclosure.affidavit_id == affidavit_id)
        .order_by(Disclosure.page_number, Disclosure.id)
    )
    disclosures = db.execute(stmt).scalars().all()

    glossary_stmt = select(LegalGlossary)
    glossary_records = db.execute(glossary_stmt).scalars().all()
    glossary_map = {item.code_key: item for item in glossary_records}

    admin_list: List[AdminDisclosureRead] = []
    for disc in disclosures:
        explanation, glossary_items = build_explanation(
            disclosure=disc,
            lang=lang,
            glossary_map=glossary_map,
        )
        review_events_read = [
            ReviewEventRead.model_validate(evt) for evt in disc.review_events
        ]
        admin_list.append(
            AdminDisclosureRead(
                id=disc.id,
                affidavit_id=disc.affidavit_id,
                category=disc.category,
                field_key=disc.field_key,
                subject_type=disc.subject_type,
                page_number=disc.page_number,
                raw_excerpt=disc.raw_excerpt,
                structured_value=disc.structured_value,
                verification_status=disc.verification_status,
                explanation=explanation,
                glossary_items=glossary_items,
                created_at=disc.created_at,
                updated_at=disc.updated_at,
                review_events=review_events_read,
            )
        )
    return admin_list


@router.patch(
    "/disclosures/{disclosure_id}",
    response_model=AdminDisclosureRead,
)
def update_disclosure_admin(
    disclosure_id: int,
    payload: DisclosurePatchRequest,
    lang: str = Query("en", description="Language code: en, te, or hi"),
    db: Session = Depends(get_db),
):
    """Update a disclosure's verification status, structured value, or page number, logging an audit ReviewEvent."""
    stmt = (
        select(Disclosure)
        .options(selectinload(Disclosure.review_events))
        .where(Disclosure.id == disclosure_id)
    )
    disclosure = db.execute(stmt).scalar_one_or_none()

    if disclosure is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Disclosure with ID {disclosure_id} not found",
        )

    previous_value = {
        "verification_status": disclosure.verification_status,
        "structured_value": disclosure.structured_value,
        "page_number": disclosure.page_number,
    }

    action_label = "admin_update"
    if payload.verification_status is not None:
        action_label = f"status_update_to_{payload.verification_status}"
        disclosure.verification_status = payload.verification_status

    if payload.structured_value is not None:
        disclosure.structured_value = payload.structured_value

    if payload.page_number is not None:
        disclosure.page_number = payload.page_number

    now_utc = datetime.now(timezone.utc)
    disclosure.updated_at = now_utc

    new_value = {
        "verification_status": disclosure.verification_status,
        "structured_value": disclosure.structured_value,
        "page_number": disclosure.page_number,
    }

    review_event = ReviewEvent(
        disclosure_id=disclosure.id,
        reviewer_name=payload.reviewer_name,
        action=action_label,
        previous_value=previous_value,
        new_value=new_value,
        review_note=payload.review_note,
        created_at=now_utc,
    )
    db.add(review_event)
    db.commit()
    db.refresh(disclosure)

    # Re-fetch with fresh review events
    stmt_updated = (
        select(Disclosure)
        .options(selectinload(Disclosure.review_events))
        .where(Disclosure.id == disclosure_id)
    )
    updated_disc = db.execute(stmt_updated).scalar_one()

    glossary_stmt = select(LegalGlossary)
    glossary_records = db.execute(glossary_stmt).scalars().all()
    glossary_map = {item.code_key: item for item in glossary_records}

    explanation, glossary_items = build_explanation(
        disclosure=updated_disc,
        lang=lang,
        glossary_map=glossary_map,
    )
    review_events_read = [
        ReviewEventRead.model_validate(evt) for evt in updated_disc.review_events
    ]

    return AdminDisclosureRead(
        id=updated_disc.id,
        affidavit_id=updated_disc.affidavit_id,
        category=updated_disc.category,
        field_key=updated_disc.field_key,
        subject_type=updated_disc.subject_type,
        page_number=updated_disc.page_number,
        raw_excerpt=updated_disc.raw_excerpt,
        structured_value=updated_disc.structured_value,
        verification_status=updated_disc.verification_status,
        explanation=explanation,
        glossary_items=glossary_items,
        created_at=updated_disc.created_at,
        updated_at=updated_disc.updated_at,
        review_events=review_events_read,
    )

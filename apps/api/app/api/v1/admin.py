from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db, verify_admin_key
from app.models.affidavit import Affidavit, Disclosure, ReviewEvent
from app.models.glossary import LegalGlossary
from app.schemas.disclosure import (
    AdminDisclosureRead,
    DisclosurePatchRequest,
    ReviewEventRead,
)
from app.services.explanations import build_explanation

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(verify_admin_key)],
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

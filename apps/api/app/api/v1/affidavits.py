from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.affidavit import Affidavit, Disclosure
from app.models.glossary import LegalGlossary
from app.schemas.disclosure import RenderedDisclosure
from app.services.explanations import build_explanation

router = APIRouter(tags=["Affidavits"])

def get_workspace_root() -> Path:
    """Find the workspace root containing 'fixtures' and 'apps'."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "fixtures").exists() and (parent / "apps").exists():
            return parent
    return current.parents[4].parent


WORKSPACE_ROOT = get_workspace_root()


@router.get(
    "/affidavits/{affidavit_id}/disclosures",
    response_model=List[RenderedDisclosure],
)
def get_affidavit_disclosures(
    affidavit_id: int,
    lang: str = Query("en", description="Language code: en, te, or hi"),
    db: Session = Depends(get_db),
):
    """Retrieve verified disclosures for an affidavit with deterministic explanations.

    STRICT GUARDRULES:
    - Enforces verification_status == 'verified' directly in the SQLAlchemy query.
    - Excludes any unverified, drafted, flagged (needs_review), or rejected disclosures.
    """
    affidavit = db.execute(
        select(Affidavit).where(Affidavit.id == affidavit_id)
    ).scalar_one_or_none()

    if affidavit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Affidavit with ID {affidavit_id} not found",
        )

    # STRICT DATABASE-LEVEL FILTER: Only verified disclosures
    disclosures_stmt = (
        select(Disclosure)
        .where(
            Disclosure.affidavit_id == affidavit_id,
            Disclosure.verification_status == "verified",
        )
        .order_by(Disclosure.page_number, Disclosure.id)
    )
    disclosures = db.execute(disclosures_stmt).scalars().all()

    # Preload legal glossary for deterministic lookup
    glossary_stmt = select(LegalGlossary)
    glossary_records = db.execute(glossary_stmt).scalars().all()
    glossary_map = {item.code_key: item for item in glossary_records}

    rendered_list: List[RenderedDisclosure] = []
    for disc in disclosures:
        explanation, glossary_items = build_explanation(
            disclosure=disc,
            lang=lang,
            glossary_map=glossary_map,
        )
        rendered_list.append(
            RenderedDisclosure(
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
            )
        )

    return rendered_list


@router.get("/affidavits/{affidavit_id}/pdf")
def get_affidavit_pdf(affidavit_id: int, db: Session = Depends(get_db)):
    """Stream the affidavit PDF with inline Content-Disposition."""
    affidavit = db.execute(
        select(Affidavit).where(Affidavit.id == affidavit_id)
    ).scalar_one_or_none()

    if affidavit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Affidavit with ID {affidavit_id} not found",
        )

    raw_path = Path(affidavit.file_path)
    if raw_path.is_absolute():
        pdf_path = raw_path
    else:
        pdf_path = WORKSPACE_ROOT / raw_path

    if not pdf_path.exists() or not pdf_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Affidavit PDF file not found on disk at {affidavit.file_path}",
        )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=affidavit_{affidavit_id}.pdf"},
    )

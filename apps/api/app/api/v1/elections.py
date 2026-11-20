from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_db
from app.models.election import Election
from app.schemas.election import ElectionRead

router = APIRouter(tags=["Elections"])


@router.get("/elections", response_model=List[ElectionRead])
def get_elections(db: Session = Depends(get_db)):
    """Fetch all elections with their nested constituencies."""
    stmt = (
        select(Election)
        .options(selectinload(Election.constituencies))
        .order_by(Election.year.desc(), Election.name)
    )
    elections = db.execute(stmt).scalars().all()
    return elections

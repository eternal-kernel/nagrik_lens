from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.glossary import LegalGlossaryItem


class ReviewEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    disclosure_id: int
    reviewer_name: str
    action: str
    previous_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    review_note: Optional[str] = None
    created_at: datetime


class RenderedDisclosure(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    affidavit_id: int
    category: str
    field_key: str
    subject_type: str
    page_number: int
    raw_excerpt: Optional[str] = None
    structured_value: Dict[str, Any]
    verification_status: str
    explanation: str
    glossary_items: List[LegalGlossaryItem] = []
    created_at: datetime
    updated_at: datetime


class AdminDisclosureRead(RenderedDisclosure):
    review_events: List[ReviewEventRead] = []


class DisclosurePatchRequest(BaseModel):
    structured_value: Optional[Dict[str, Any]] = None
    page_number: Optional[int] = None
    verification_status: Optional[str] = None
    review_note: Optional[str] = None
    reviewer_name: str = "Admin Reviewer"

    @field_validator("verification_status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"draft", "needs_review", "verified", "rejected"}
            if v not in allowed:
                raise ValueError(
                    f"Invalid verification_status '{v}'. Must be one of: {', '.join(sorted(allowed))}"
                )
        return v

from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class PublicActivityRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_type: str
    period_label: str
    source_name: str
    source_url: str
    structured_payload: dict
    explanations: Dict[str, str] = Field(..., description="Deterministic plain-language explanations in en, te, hi")
    verification_status: str


class FiveYearPreview(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    is_incumbent: bool
    prior_office_held: Optional[str] = None
    works_completed: Optional[int] = None
    works_recommended: Optional[int] = None
    attendance_pct: Optional[int] = None
    verified_records_count: int = 0

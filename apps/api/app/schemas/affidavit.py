from datetime import date, datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict


class AffidavitSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    source_url: Optional[str] = None
    file_path: str
    file_hash: str
    filing_date: date
    processing_status: str
    publication_status: str
    redaction_boxes: Optional[Dict[str, Any]] = None
    created_at: datetime

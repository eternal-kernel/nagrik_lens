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


class AffidavitUploadResponse(BaseModel):
    affidavit: AffidavitSummary
    inspection: Dict[str, Any]


class AffidavitExtractionResponse(BaseModel):
    affidavit_id: int
    processing_status: str
    pages_inspected: int
    ocr_pages_detected: int
    disclosures_extracted: int
    warnings: list[str] = []


class AdminAffidavitListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    candidate_name: str
    filing_date: date
    processing_status: str
    publication_status: str
    disclosure_count: int
    needs_review_count: int

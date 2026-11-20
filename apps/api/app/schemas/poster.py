from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CandidateMatchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: int
    name: str
    display_name: str
    party_name: str
    constituency_name: str
    constituency_code: Optional[str] = None
    election_name: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0, description="Match confidence score between 0.0 and 1.0")
    matched_terms: List[str] = Field(default_factory=list, description="Terms that matched or contributed to score")


class PosterScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ocr_text: str = Field(..., description="Raw text extracted from image via OCR")
    matches: List[CandidateMatchItem] = Field(default_factory=list, description="Ranked candidate matches")
    requires_disambiguation: bool = Field(..., description="True if disambiguation is required (multiple matches or confidence < 0.75)")
    detected_constituency: Optional[str] = Field(None, description="Constituency name or code detected in poster")
    detected_party: Optional[str] = Field(None, description="Political party name detected in poster")
    message: Optional[str] = Field(None, description="Guidance or informational message")

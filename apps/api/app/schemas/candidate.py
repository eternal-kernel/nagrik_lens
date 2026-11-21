from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.election import ConstituencyRead, ElectionRead
from app.schemas.affidavit import AffidavitSummary
from app.schemas.public_record import PublicActivityRecordOut


class CandidateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    constituency_id: int
    name: str
    display_name: str
    party_name: str
    is_fictional: bool
    prior_office_held: Optional[str] = None
    created_at: datetime
    constituency_name: Optional[str] = None
    election_name: Optional[str] = None


class CandidateDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    constituency_id: int
    name: str
    display_name: str
    party_name: str
    is_fictional: bool
    prior_office_held: Optional[str] = None
    created_at: datetime
    constituency: ConstituencyRead
    election: Optional[ElectionRead] = None
    affidavits: List[AffidavitSummary] = []
    public_records: List[PublicActivityRecordOut] = []

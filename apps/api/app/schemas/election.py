from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict


class ConstituencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    election_id: int
    name: str
    code: str
    state: str


class ElectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    election_type: str
    year: int
    state: str
    created_at: datetime
    constituencies: List[ConstituencyRead] = []

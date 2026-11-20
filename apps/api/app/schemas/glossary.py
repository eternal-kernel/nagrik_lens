from pydantic import BaseModel, ConfigDict


class LegalGlossaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code_key: str
    act_name: str
    term: str
    explanation: str
    review_status: str = "verified"

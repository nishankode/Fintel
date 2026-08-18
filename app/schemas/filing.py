from datetime import date

from pydantic import BaseModel, Field


class FilingCreateRequest(BaseModel):

    company_id: int = Field(gt=0)
    accession_number: str = Field(min_length=1, max_length=32)
    filing_type: str = Field(min_length=1, max_length=20)
    filed_at: date
    reporting_period: date | None
    source_url: str = Field(min_length=1, max_length=1000)


class FilingResponse(BaseModel):
    id: int
    company_id: int
    accession_number: str
    filing_type: str
    filed_at: date
    reporting_period: date | None
    source_url: str
    status: str

    model_config = {
        "from_attributes": True
    }
from pydantic import BaseModel, Field


class CompanyIngestionRequest(BaseModel):
    filing_types: set[str] | None = None
    limit: int | None = Field(default=None, gt=0)


class FilingIngestionResponse(BaseModel):
    filing_id: int
    accession_number: str
    status: str
    chunks_embedded: int


class CompanyIngestionResponse(BaseModel):
    company_id: int
    ticker: str
    discovered_new_filings: int
    processed_filings: list[FilingIngestionResponse]

from datetime import date

from pydantic import BaseModel, Field


class SemanticSearchFilterRequest(BaseModel):
    company_id: int | None = Field(default=None, gt=0)
    ticker: str | None = Field(default=None, min_length=1, max_length=10)
    filing_type: str | None = Field(default=None, min_length=1, max_length=20)
    section_key: str | None = Field(default=None, min_length=1, max_length=100)
    filed_from: date | None = None
    filed_to: date | None = None


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, gt=0, le=50)
    filters: SemanticSearchFilterRequest | None = None


class SemanticSearchResultResponse(BaseModel):
    chunk_id: int
    filing_id: int
    company_id: int
    ticker: str
    accession_number: str
    filing_type: str
    filed_at: date
    section_key: str
    chunk_index: int
    text: str
    cosine_distance: float
    cosine_similarity: float


class SemanticSearchResponse(BaseModel):
    query: str
    top_k: int
    results: list[SemanticSearchResultResponse]

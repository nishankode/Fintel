from pydantic import BaseModel, Field

from app.schemas.retrieval import SemanticSearchFilterRequest


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, gt=0, le=50)
    filters: SemanticSearchFilterRequest | None = None


class EvidenceCitationResponse(BaseModel):
    citation_id: str
    chunk_id: int
    filing_id: int
    company_id: int
    ticker: str
    accession_number: str
    filing_type: str
    section_key: str
    chunk_index: int
    text: str
    cosine_distance: float
    cosine_similarity: float


class QueryResponse(BaseModel):
    question: str
    answer: str
    evidence: list[EvidenceCitationResponse]

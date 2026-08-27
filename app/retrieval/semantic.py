from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings.service import EmbeddingService
from app.models import Chunk, Company, Filing


@dataclass(frozen=True)
class SemanticSearchFilters:
    company_id: int | None = None
    ticker: str | None = None
    filing_type: str | None = None
    section_key: str | None = None
    filed_from: date | None = None
    filed_to: date | None = None


@dataclass
class SemanticSearchResult:
    chunk: Chunk
    cosine_distance: float
    filing: Filing
    company: Company

    @property
    def cosine_similarity(self) -> float:
        return 1.0 - self.cosine_distance


class SemanticRetriever:
    def __init__(
        self,
        db: Session,
        embedding_service: EmbeddingService,
    ) -> None:
        self.db = db
        self.embedding_service = embedding_service

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: SemanticSearchFilters | None = None,
    ) -> list[SemanticSearchResult]:
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError(
                "Semantic search query must not be blank"
            )

        if top_k <= 0:
            raise ValueError(
                "Semantic search top_k must be greater than zero"
            )

        query_embedding = (
            self.embedding_service.embed_query(
                normalized_query
            )
        )

        distance = (
            Chunk.embedding.cosine_distance(
                query_embedding
            )
        )

        statement = (
            select(
                Chunk,
                Filing,
                Company,
                distance.label("cosine_distance"),
            )
            .join(Filing, Chunk.filing_id == Filing.id)
            .join(Company, Filing.company_id == Company.id)
            .where(
                Chunk.embedding.is_not(None)
            )
            .order_by(distance)
            .limit(top_k)
        )

        if filters is not None:
            if filters.company_id is not None:
                statement = statement.where(
                    Filing.company_id == filters.company_id
                )

            if filters.ticker is not None:
                statement = statement.where(
                    Company.ticker == filters.ticker.upper()
                )

            if filters.filing_type is not None:
                statement = statement.where(
                    Filing.filing_type == filters.filing_type.upper()
                )

            if filters.section_key is not None:
                statement = statement.where(
                    Chunk.section_key == filters.section_key
                )

            if filters.filed_from is not None:
                statement = statement.where(
                    Filing.filed_at >= filters.filed_from
                )

            if filters.filed_to is not None:
                statement = statement.where(
                    Filing.filed_at <= filters.filed_to
                )

        rows = self.db.execute(statement).all()

        return [
            SemanticSearchResult(
                chunk=chunk,
                filing=filing,
                company=company,
                cosine_distance=float(
                    cosine_distance
                ),
            )
            for chunk, filing, company, cosine_distance in rows
        ]

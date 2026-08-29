from dataclasses import dataclass

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models import Chunk, Company, Filing
from app.retrieval.semantic import SemanticSearchFilters


@dataclass
class LexicalSearchResult:
    chunk: Chunk
    filing: Filing
    company: Company
    lexical_score: float


class LexicalRetriever:
    def __init__(
        self,
        db: Session,
    ) -> None:
        self.db = db

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: SemanticSearchFilters | None = None,
    ) -> list[LexicalSearchResult]:
        normalized_query = query.strip()

        if not normalized_query:
            raise ValueError(
                "Lexical search query must not be blank"
            )

        if top_k <= 0:
            raise ValueError(
                "Lexical search top_k must be greater than zero"
            )

        document = func.to_tsvector(
            "english",
            Chunk.text,
        )
        query_document = func.plainto_tsquery(
            "english",
            normalized_query,
        )
        score = func.ts_rank_cd(
            document,
            query_document,
        )

        statement = (
            select(
                Chunk,
                Filing,
                Company,
                score.label("lexical_score"),
            )
            .join(Filing, Chunk.filing_id == Filing.id)
            .join(Company, Filing.company_id == Company.id)
            .where(document.op("@@")(query_document))
            .order_by(score.desc())
            .limit(top_k)
        )

        statement = _apply_filters(
            statement=statement,
            filters=filters,
        )

        rows = self.db.execute(statement).all()

        return [
            LexicalSearchResult(
                chunk=chunk,
                filing=filing,
                company=company,
                lexical_score=float(lexical_score),
            )
            for chunk, filing, company, lexical_score in rows
        ]


def _apply_filters(
    statement,
    filters: SemanticSearchFilters | None,
):
    if filters is None:
        return statement

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

    if filters.filing_types is not None:
        statement = statement.where(
            Filing.filing_type.in_(
                {
                    filing_type.upper()
                    for filing_type in filters.filing_types
                }
            )
        )

    if filters.filing_years is not None:
        statement = statement.where(
            extract("year", Filing.filed_at).in_(
                filters.filing_years
            )
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

    return statement

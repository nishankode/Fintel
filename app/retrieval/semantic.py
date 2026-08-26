from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings.service import EmbeddingService
from app.models import Chunk


@dataclass
class SemanticSearchResult:
    chunk: Chunk
    cosine_distance: float

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

        rows = self.db.execute(
            select(
                Chunk,
                distance.label(
                    "cosine_distance"
                ),
            )
            .where(
                Chunk.embedding.is_not(None)
            )
            .order_by(distance)
            .limit(top_k)
        ).all()

        return [
            SemanticSearchResult(
                chunk=chunk,
                cosine_distance=float(
                    cosine_distance
                ),
            )
            for chunk, cosine_distance in rows
        ]

from dataclasses import dataclass

from app.models import Chunk, Company, Filing
from app.retrieval.lexical import LexicalRetriever
from app.retrieval.semantic import (
    SemanticRetriever,
    SemanticSearchFilters,
)


@dataclass
class HybridSearchResult:
    chunk: Chunk
    filing: Filing
    company: Company
    rrf_score: float
    semantic_rank: int | None
    lexical_rank: int | None
    cosine_distance: float | None
    cosine_similarity: float | None


class HybridRetriever:
    def __init__(
        self,
        semantic_retriever: SemanticRetriever,
        lexical_retriever: LexicalRetriever,
        rrf_k: int = 60,
    ) -> None:
        self.semantic_retriever = semantic_retriever
        self.lexical_retriever = lexical_retriever
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: SemanticSearchFilters | None = None,
    ) -> list[HybridSearchResult]:
        semantic_results = self.semantic_retriever.search(
            query=query,
            top_k=top_k,
            filters=filters,
        )
        lexical_results = self.lexical_retriever.search(
            query=query,
            top_k=top_k,
            filters=filters,
        )

        fused: dict[int, HybridSearchResult] = {}

        for rank, result in enumerate(
            semantic_results,
            start=1,
        ):
            fused[result.chunk.id] = HybridSearchResult(
                chunk=result.chunk,
                filing=result.filing,
                company=result.company,
                rrf_score=_rrf_score(
                    rank=rank,
                    rrf_k=self.rrf_k,
                ),
                semantic_rank=rank,
                lexical_rank=None,
                cosine_distance=result.cosine_distance,
                cosine_similarity=result.cosine_similarity,
            )

        for rank, result in enumerate(
            lexical_results,
            start=1,
        ):
            existing = fused.get(result.chunk.id)

            if existing is None:
                fused[result.chunk.id] = HybridSearchResult(
                    chunk=result.chunk,
                    filing=result.filing,
                    company=result.company,
                    rrf_score=_rrf_score(
                        rank=rank,
                        rrf_k=self.rrf_k,
                    ),
                    semantic_rank=None,
                    lexical_rank=rank,
                    cosine_distance=None,
                    cosine_similarity=None,
                )
                continue

            existing.rrf_score += _rrf_score(
                rank=rank,
                rrf_k=self.rrf_k,
            )
            existing.lexical_rank = rank

        return sorted(
            fused.values(),
            key=lambda result: result.rrf_score,
            reverse=True,
        )[:top_k]


def _rrf_score(
    rank: int,
    rrf_k: int,
) -> float:
    return 1.0 / (rrf_k + rank)

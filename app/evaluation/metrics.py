from dataclasses import dataclass
from math import log2

from app.retrieval.semantic import (
    SemanticRetriever,
    SemanticSearchFilters,
)


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    query: str
    expected_chunk_ids: set[int]
    top_k: int = 5
    filters: SemanticSearchFilters | None = None


@dataclass(frozen=True)
class RetrievalEvaluationResult:
    query: str
    retrieved_chunk_ids: list[int]
    expected_chunk_ids: set[int]
    recall_at_k: float
    reciprocal_rank: float
    ndcg_at_k: float


class RetrievalEvaluator:
    def __init__(
        self,
        retriever: SemanticRetriever,
    ) -> None:
        self.retriever = retriever

    def evaluate_case(
        self,
        evaluation_case: RetrievalEvaluationCase,
    ) -> RetrievalEvaluationResult:
        results = self.retriever.search(
            query=evaluation_case.query,
            top_k=evaluation_case.top_k,
            filters=evaluation_case.filters,
        )
        retrieved_chunk_ids = [
            result.chunk.id
            for result in results
        ]

        return RetrievalEvaluationResult(
            query=evaluation_case.query,
            retrieved_chunk_ids=retrieved_chunk_ids,
            expected_chunk_ids=evaluation_case.expected_chunk_ids,
            recall_at_k=recall_at_k(
                retrieved_chunk_ids=retrieved_chunk_ids,
                expected_chunk_ids=evaluation_case.expected_chunk_ids,
            ),
            reciprocal_rank=reciprocal_rank(
                retrieved_chunk_ids=retrieved_chunk_ids,
                expected_chunk_ids=evaluation_case.expected_chunk_ids,
            ),
            ndcg_at_k=ndcg_at_k(
                retrieved_chunk_ids=retrieved_chunk_ids,
                expected_chunk_ids=evaluation_case.expected_chunk_ids,
            ),
        )

    def evaluate(
        self,
        evaluation_cases: list[RetrievalEvaluationCase],
    ) -> list[RetrievalEvaluationResult]:
        return [
            self.evaluate_case(evaluation_case)
            for evaluation_case in evaluation_cases
        ]


def recall_at_k(
    retrieved_chunk_ids: list[int],
    expected_chunk_ids: set[int],
) -> float:
    if not expected_chunk_ids:
        return 0.0

    retrieved_expected = (
        set(retrieved_chunk_ids) & expected_chunk_ids
    )

    return len(retrieved_expected) / len(expected_chunk_ids)


def reciprocal_rank(
    retrieved_chunk_ids: list[int],
    expected_chunk_ids: set[int],
) -> float:
    for index, chunk_id in enumerate(
        retrieved_chunk_ids,
        start=1,
    ):
        if chunk_id in expected_chunk_ids:
            return 1.0 / index

    return 0.0


def ndcg_at_k(
    retrieved_chunk_ids: list[int],
    expected_chunk_ids: set[int],
) -> float:
    dcg = 0.0

    for index, chunk_id in enumerate(
        retrieved_chunk_ids,
        start=1,
    ):
        if chunk_id in expected_chunk_ids:
            dcg += 1.0 / log2(index + 1)

    ideal_hits = min(
        len(expected_chunk_ids),
        len(retrieved_chunk_ids),
    )
    ideal_dcg = sum(
        1.0 / log2(index + 1)
        for index in range(1, ideal_hits + 1)
    )

    if ideal_dcg == 0.0:
        return 0.0

    return dcg / ideal_dcg

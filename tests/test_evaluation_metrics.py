import unittest
from unittest.mock import Mock

from app.evaluation.metrics import (
    RetrievalEvaluationCase,
    RetrievalEvaluator,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
)


class RetrievalMetricTests(unittest.TestCase):
    def test_recall_at_k_counts_expected_hits(self):
        self.assertEqual(
            recall_at_k(
                retrieved_chunk_ids=[10, 20, 30],
                expected_chunk_ids={20, 40},
            ),
            0.5,
        )

    def test_reciprocal_rank_uses_first_relevant_hit(self):
        self.assertEqual(
            reciprocal_rank(
                retrieved_chunk_ids=[10, 20, 30],
                expected_chunk_ids={30},
            ),
            1 / 3,
        )

    def test_ndcg_rewards_earlier_relevant_results(self):
        better = ndcg_at_k(
            retrieved_chunk_ids=[10, 20, 30],
            expected_chunk_ids={10, 20},
        )
        worse = ndcg_at_k(
            retrieved_chunk_ids=[30, 20, 10],
            expected_chunk_ids={10, 20},
        )

        self.assertGreater(better, worse)


class RetrievalEvaluatorTests(unittest.TestCase):
    def test_evaluates_retriever_results_against_expected_chunks(self):
        retriever = Mock()
        retriever.search.return_value = [
            SearchResultStub(chunk_id=101),
            SearchResultStub(chunk_id=202),
        ]
        evaluator = RetrievalEvaluator(
            retriever=retriever,
        )

        result = evaluator.evaluate_case(
            RetrievalEvaluationCase(
                query="cloud revenue",
                expected_chunk_ids={202},
                top_k=2,
            )
        )

        retriever.search.assert_called_once_with(
            query="cloud revenue",
            top_k=2,
            filters=None,
        )
        self.assertEqual(result.retrieved_chunk_ids, [101, 202])
        self.assertEqual(result.recall_at_k, 1.0)
        self.assertEqual(result.reciprocal_rank, 0.5)


class SearchResultStub:
    def __init__(
        self,
        chunk_id: int,
    ) -> None:
        self.chunk = ChunkStub(
            id=chunk_id,
        )


class ChunkStub:
    def __init__(
        self,
        id: int,
    ) -> None:
        self.id = id


if __name__ == "__main__":
    unittest.main()

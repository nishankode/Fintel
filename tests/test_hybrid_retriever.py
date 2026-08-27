import unittest
from datetime import date
from unittest.mock import Mock

from app.models import Chunk, Company, Filing
from app.retrieval.hybrid import HybridRetriever, _rrf_score
from app.retrieval.lexical import LexicalSearchResult
from app.retrieval.semantic import SemanticSearchResult


class HybridRetrieverTests(unittest.TestCase):
    def test_rrf_score_decreases_as_rank_gets_worse(self):
        self.assertGreater(
            _rrf_score(rank=1, rrf_k=60),
            _rrf_score(rank=2, rrf_k=60),
        )

    def test_combines_semantic_and_lexical_rankings(self):
        shared = self._chunk(1)
        semantic_only = self._chunk(2)
        lexical_only = self._chunk(3)

        semantic_retriever = Mock()
        semantic_retriever.search.return_value = [
            self._semantic_result(semantic_only),
            self._semantic_result(shared),
        ]
        lexical_retriever = Mock()
        lexical_retriever.search.return_value = [
            self._lexical_result(shared),
            self._lexical_result(lexical_only),
        ]
        retriever = HybridRetriever(
            semantic_retriever=semantic_retriever,
            lexical_retriever=lexical_retriever,
            rrf_k=60,
        )

        results = retriever.search(
            query="revenue growth",
            top_k=3,
        )

        self.assertEqual(
            results[0].chunk.id,
            shared.id,
        )
        self.assertEqual(
            results[0].semantic_rank,
            2,
        )
        self.assertEqual(
            results[0].lexical_rank,
            1,
        )

    def _semantic_result(
        self,
        chunk: Chunk,
    ) -> SemanticSearchResult:
        return SemanticSearchResult(
            chunk=chunk,
            filing=self._filing(),
            company=self._company(),
            cosine_distance=0.1,
        )

    def _lexical_result(
        self,
        chunk: Chunk,
    ) -> LexicalSearchResult:
        return LexicalSearchResult(
            chunk=chunk,
            filing=self._filing(),
            company=self._company(),
            lexical_score=1.0,
        )

    def _chunk(
        self,
        chunk_id: int,
    ) -> Chunk:
        return Chunk(
            id=chunk_id,
            filing_id=1,
            section_key="mdna",
            chunk_index=chunk_id,
            text=f"chunk {chunk_id}",
            character_count=7,
            embedding=[1.0] * 384,
        )

    def _filing(self) -> Filing:
        return Filing(
            id=1,
            company_id=1,
            accession_number="0000000001-26-000001",
            filing_type="10-K",
            filed_at=date(2026, 1, 1),
            reporting_period=None,
            source_url="https://example.com/filing.htm",
            status="indexed",
        )

    def _company(self) -> Company:
        return Company(
            id=1,
            cik="0000000001",
            ticker="ACME",
            name="Acme Inc.",
        )


if __name__ == "__main__":
    unittest.main()

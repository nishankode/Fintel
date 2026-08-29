import unittest
from datetime import date
from unittest.mock import Mock

from app.llm.service import GeneratedAnswer
from app.models import Chunk, Company, Filing
from app.rag.context import RetrievalContextBuilder
from app.rag.service import RAGAnswerService
from app.retrieval.hybrid import HybridSearchResult
from app.retrieval.semantic import SemanticSearchResult
from app.schemas.query import QueryRequest
from app.schemas.retrieval import SemanticSearchFilterRequest


class RetrievalContextBuilderTests(unittest.TestCase):
    def test_builds_citation_order_from_retrieval_results(self):
        builder = RetrievalContextBuilder(
            max_chunk_characters=12,
        )

        context = builder.build(
            [
                self._result(
                    chunk_id=1,
                    text="Revenue increased significantly.",
                ),
                self._result(
                    chunk_id=2,
                    text="Margins improved.",
                ),
            ]
        )

        self.assertEqual(
            [chunk.citation_id for chunk in context.evidence_chunks],
            ["E1", "E2"],
        )
        self.assertEqual(
            context.evidence_chunks[0].text,
            "Revenue incr",
        )
        self.assertIn(
            "[E1] ACME 10-K mdna chunk 0",
            context.as_prompt_text(),
        )

    def test_builds_context_from_lexical_only_hybrid_result(self):
        builder = RetrievalContextBuilder()

        context = builder.build(
            [
                self._hybrid_result(
                    chunk_id=1,
                    text="Revenue increased significantly.",
                )
            ]
        )

        self.assertEqual(
            context.evidence_chunks[0].citation_id,
            "E1",
        )
        self.assertIsNone(
            context.evidence_chunks[0].cosine_distance,
        )

    def _result(
        self,
        chunk_id: int,
        text: str,
    ) -> SemanticSearchResult:
        company = Company(
            id=1,
            cik="0000000001",
            ticker="ACME",
            name="Acme Inc.",
        )
        filing = Filing(
            id=1,
            company_id=1,
            accession_number="0000000001-26-000001",
            filing_type="10-K",
            filed_at=date(2026, 1, 1),
            reporting_period=None,
            source_url="https://example.com/filing.htm",
            status="indexed",
        )
        chunk = Chunk(
            id=chunk_id,
            filing_id=1,
            section_key="mdna",
            chunk_index=chunk_id - 1,
            text=text,
            character_count=len(text),
            embedding=[1.0] * 384,
        )

        return SemanticSearchResult(
            chunk=chunk,
            filing=filing,
            company=company,
            cosine_distance=0.1,
        )

    def _hybrid_result(
        self,
        chunk_id: int,
        text: str,
    ) -> HybridSearchResult:
        semantic_result = self._result(
            chunk_id=chunk_id,
            text=text,
        )

        return HybridSearchResult(
            chunk=semantic_result.chunk,
            filing=semantic_result.filing,
            company=semantic_result.company,
            rrf_score=1.0,
            semantic_rank=None,
            lexical_rank=1,
            cosine_distance=None,
            cosine_similarity=None,
        )


class QueryRequestTests(unittest.TestCase):
    def test_defaults_to_semantic_retrieval(self):
        request = QueryRequest(
            question="How did revenue change?",
        )

        self.assertEqual(
            request.retrieval_mode,
            "semantic",
        )

    def test_accepts_hybrid_retrieval_mode(self):
        request = QueryRequest(
            question="How did revenue change?",
            retrieval_mode="hybrid",
        )

        self.assertEqual(
            request.retrieval_mode,
            "hybrid",
        )

    def test_accepts_session_scoped_retrieval_filters(self):
        request = QueryRequest(
            question="How did revenue change?",
            filters=SemanticSearchFilterRequest(
                ticker="AAPL",
                filing_types={"10-K", "10-Q"},
                filing_years={2024, 2025},
            ),
        )

        self.assertEqual(request.filters.ticker, "AAPL")
        self.assertEqual(
            request.filters.filing_types,
            {"10-K", "10-Q"},
        )
        self.assertEqual(
            request.filters.filing_years,
            {2024, 2025},
        )


class RAGAnswerServiceTests(unittest.TestCase):
    def test_retrieves_context_and_generates_grounded_answer(self):
        retriever = Mock()
        retriever.search.return_value = [
            RetrievalContextBuilderTests()._result(
                chunk_id=1,
                text="Revenue increased.",
            )
        ]
        llm = Mock()
        llm.generate_answer.return_value = GeneratedAnswer(
            answer="Revenue increased according to the filing."
        )

        service = RAGAnswerService(
            retriever=retriever,
            context_builder=RetrievalContextBuilder(),
            llm=llm,
        )

        answer = service.answer(
            question="How did revenue change?",
            top_k=3,
        )

        retriever.search.assert_called_once_with(
            query="How did revenue change?",
            top_k=3,
            filters=None,
        )
        llm.generate_answer.assert_called_once()
        self.assertEqual(
            answer.answer,
            "Revenue increased according to the filing.",
        )
        self.assertEqual(answer.evidence[0].citation_id, "E1")


if __name__ == "__main__":
    unittest.main()

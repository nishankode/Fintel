import unittest
from datetime import date
from unittest.mock import Mock

from app.llm.service import GeneratedAnswer
from app.models import Chunk, Company, Filing
from app.rag.context import RetrievalContextBuilder
from app.rag.service import RAGAnswerService
from app.retrieval.semantic import SemanticSearchResult


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

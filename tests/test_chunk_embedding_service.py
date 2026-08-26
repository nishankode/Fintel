import unittest
from datetime import date
from unittest.mock import Mock

from app.ingestion.embeddings import ChunkEmbeddingService
from app.models import Chunk, Filing


class ScalarResultStub:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class ChunkEmbeddingServiceTests(unittest.TestCase):
    def test_embeds_only_missing_chunk_embeddings_in_batches(self):
        filing = self._filing(status="chunks_created")
        chunks = [
            self._chunk(index=0),
            self._chunk(index=1),
            self._chunk(index=2),
        ]

        db = Mock()
        db.scalar.return_value = len(chunks)
        db.scalars.return_value = ScalarResultStub(chunks)

        embedding_service = Mock()
        embedding_service.embed_documents.side_effect = [
            [[1.0] * 384, [2.0] * 384],
            [[3.0] * 384],
        ]

        service = ChunkEmbeddingService(
            db=db,
            embedding_service=embedding_service,
            batch_size=2,
        )

        embedded_count = service.embed_filing_chunks(filing)

        self.assertEqual(embedded_count, 3)
        self.assertEqual(filing.status, "indexed")
        self.assertEqual(db.commit.call_count, 3)
        embedding_service.embed_documents.assert_any_call(
            ["chunk 0", "chunk 1"]
        )
        embedding_service.embed_documents.assert_any_call(
            ["chunk 2"]
        )

    def test_marks_filing_indexed_when_rerun_finds_all_chunks_embedded(self):
        filing = self._filing(status="chunks_created")

        db = Mock()
        db.scalar.return_value = 2
        db.scalars.return_value = ScalarResultStub([])

        embedding_service = Mock()

        service = ChunkEmbeddingService(
            db=db,
            embedding_service=embedding_service,
        )

        embedded_count = service.embed_filing_chunks(filing)

        self.assertEqual(embedded_count, 0)
        self.assertEqual(filing.status, "indexed")
        db.commit.assert_called_once()
        embedding_service.embed_documents.assert_not_called()

    def test_does_not_mark_empty_filing_as_indexed(self):
        filing = self._filing(status="pending")

        db = Mock()
        db.scalar.return_value = 0

        embedding_service = Mock()

        service = ChunkEmbeddingService(
            db=db,
            embedding_service=embedding_service,
        )

        embedded_count = service.embed_filing_chunks(filing)

        self.assertEqual(embedded_count, 0)
        self.assertEqual(filing.status, "pending")
        db.commit.assert_not_called()
        embedding_service.embed_documents.assert_not_called()

    def test_rolls_back_and_reraises_when_batch_persistence_fails(self):
        filing = self._filing(status="chunks_created")
        chunks = [self._chunk(index=0)]

        db = Mock()
        db.scalar.return_value = 1
        db.scalars.return_value = ScalarResultStub(chunks)
        db.commit.side_effect = RuntimeError("database unavailable")

        embedding_service = Mock()
        embedding_service.embed_documents.return_value = [[1.0] * 384]

        service = ChunkEmbeddingService(
            db=db,
            embedding_service=embedding_service,
        )

        with self.assertLogs(
            "app.ingestion.embeddings",
            level="ERROR",
        ):
            with self.assertRaises(RuntimeError):
                service.embed_filing_chunks(filing)

        db.rollback.assert_called_once()
        self.assertEqual(filing.status, "chunks_created")

    def _filing(self, status: str) -> Filing:
        return Filing(
            id=1,
            company_id=1,
            accession_number="0000000000-26-000001",
            filing_type="10-K",
            filed_at=date(2026, 1, 1),
            reporting_period=None,
            source_url="https://example.com/filing.htm",
            status=status,
        )

    def _chunk(self, index: int) -> Chunk:
        return Chunk(
            id=index + 1,
            filing_id=1,
            section_key="business",
            chunk_index=index,
            text=f"chunk {index}",
            character_count=7,
        )


if __name__ == "__main__":
    unittest.main()

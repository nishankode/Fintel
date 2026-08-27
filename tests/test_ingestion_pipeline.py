import unittest
from datetime import date
from unittest.mock import Mock

from app.ingestion.pipeline import FilingIngestionPipeline
from app.ingestion.schemas import ParsedFilingDocument
from app.models import Filing


class FilingIngestionPipelineTests(unittest.TestCase):
    def test_ingests_filing_through_storage_parse_chunk_and_embed(self):
        filing = self._filing(status="pending")

        db = Mock()
        document_service = Mock()
        document_service.download_and_store.return_value = (
            "filings/ACME/000000000026000001/report.htm"
        )
        storage = Mock()
        storage.read_text.return_value = "<html>Revenue increased.</html>"
        parser_service = Mock()
        parser_service.parse.return_value = ParsedFilingDocument(
            text="Revenue increased.",
            character_count=18,
            sections=[],
        )
        chunk_service = Mock()
        embedding_service = Mock()

        def embed_filing_chunks(target_filing):
            target_filing.status = "indexed"
            return 4

        embedding_service.embed_filing_chunks.side_effect = (
            embed_filing_chunks
        )

        pipeline = FilingIngestionPipeline(
            db=db,
            filing_document_service=document_service,
            storage=storage,
            parser_service=parser_service,
            chunk_service=chunk_service,
            chunk_embedding_service=embedding_service,
        )

        result = pipeline.ingest_filing(filing)

        document_service.download_and_store.assert_called_once_with(
            filing
        )
        storage.read_text.assert_called_once_with(
            "filings/ACME/000000000026000001/report.htm"
        )
        parser_service.parse.assert_called_once_with(
            html="<html>Revenue increased.</html>",
            filing_type="10-K",
        )
        chunk_service.create_chunks.assert_called_once()
        embedding_service.embed_filing_chunks.assert_called_once_with(
            filing
        )
        db.refresh.assert_called_once_with(filing)
        self.assertEqual(db.commit.call_count, 3)
        self.assertEqual(result.status, "indexed")
        self.assertEqual(result.chunks_embedded, 4)

    def test_skips_already_indexed_filing(self):
        filing = self._filing(status="indexed")

        db = Mock()
        pipeline = FilingIngestionPipeline(
            db=db,
            filing_document_service=Mock(),
            storage=Mock(),
            parser_service=Mock(),
            chunk_service=Mock(),
            chunk_embedding_service=Mock(),
        )

        result = pipeline.ingest_filing(filing)

        self.assertEqual(result.status, "indexed")
        self.assertEqual(result.chunks_embedded, 0)
        db.commit.assert_not_called()

    def test_marks_filing_failed_when_pipeline_step_fails(self):
        filing = self._filing(status="pending")

        db = Mock()
        document_service = Mock()
        document_service.download_and_store.side_effect = RuntimeError(
            "SEC unavailable"
        )

        pipeline = FilingIngestionPipeline(
            db=db,
            filing_document_service=document_service,
            storage=Mock(),
            parser_service=Mock(),
            chunk_service=Mock(),
            chunk_embedding_service=Mock(),
        )

        with self.assertLogs(
            "app.ingestion.pipeline",
            level="ERROR",
        ):
            with self.assertRaises(RuntimeError):
                pipeline.ingest_filing(filing)

        db.rollback.assert_called_once()
        db.commit.assert_called_once()
        self.assertEqual(filing.status, "failed")

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


if __name__ == "__main__":
    unittest.main()

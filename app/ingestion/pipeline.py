import logging
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.chunks import FilingChunkService
from app.ingestion.documents import FilingDocumentService
from app.ingestion.embeddings import ChunkEmbeddingService
from app.ingestion.parser import FilingParserService
from app.ingestion.persistence import SECFilingPersistenceService
from app.models import Company, Filing
from app.storage.local import LocalDocumentStorage


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FilingIngestionResult:
    filing_id: int
    accession_number: str
    status: str
    chunks_embedded: int


@dataclass(frozen=True)
class CompanyIngestionResult:
    company_id: int
    ticker: str
    discovered_new_filings: int
    processed_filings: list[FilingIngestionResult]


class FilingIngestionPipeline:
    def __init__(
        self,
        db: Session,
        filing_document_service: FilingDocumentService,
        storage: LocalDocumentStorage,
        parser_service: FilingParserService,
        chunk_service: FilingChunkService,
        chunk_embedding_service: ChunkEmbeddingService,
    ) -> None:
        self.db = db
        self.filing_document_service = filing_document_service
        self.storage = storage
        self.parser_service = parser_service
        self.chunk_service = chunk_service
        self.chunk_embedding_service = chunk_embedding_service

    def ingest_filing(
        self,
        filing: Filing,
    ) -> FilingIngestionResult:
        if filing.status == "indexed":
            logger.info(
                "Filing already indexed: filing_id=%s",
                filing.id,
            )
            return FilingIngestionResult(
                filing_id=filing.id,
                accession_number=filing.accession_number,
                status=filing.status,
                chunks_embedded=0,
            )

        try:
            storage_key = (
                self.filing_document_service.download_and_store(
                    filing
                )
            )

            filing.status = "stored"
            self.db.commit()

            html = self.storage.read_text(storage_key)

            parsed_document = self.parser_service.parse(
                html=html,
                filing_type=filing.filing_type,
            )

            filing.status = "parsed"
            self.db.commit()

            self.chunk_service.create_chunks(
                filing=filing,
                document=parsed_document,
            )

            filing.status = "chunked"
            self.db.commit()

            chunks_embedded = (
                self.chunk_embedding_service.embed_filing_chunks(
                    filing
                )
            )

            self.db.refresh(filing)

            return FilingIngestionResult(
                filing_id=filing.id,
                accession_number=filing.accession_number,
                status=filing.status,
                chunks_embedded=chunks_embedded,
            )
        except Exception:
            self.db.rollback()
            filing.status = "failed"
            self.db.commit()

            logger.exception(
                "Filing ingestion failed: filing_id=%s",
                filing.id,
            )

            raise


class CompanyIngestionPipeline:
    def __init__(
        self,
        db: Session,
        filing_persistence_service: SECFilingPersistenceService,
        filing_ingestion_pipeline: FilingIngestionPipeline,
    ) -> None:
        self.db = db
        self.filing_persistence_service = filing_persistence_service
        self.filing_ingestion_pipeline = filing_ingestion_pipeline

    def ingest_company(
        self,
        company: Company,
        filing_types: set[str] | None = None,
        limit: int | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> CompanyIngestionResult:
        new_filings = (
            self.filing_persistence_service.sync_company_filings(
                company=company,
                filing_types=filing_types,
            )
        )

        query = (
            select(Filing)
            .where(
                Filing.company_id == company.id,
                Filing.status != "indexed",
            )
            .order_by(Filing.filed_at.desc())
        )

        if filing_types:
            normalized_types = {
                filing_type.upper()
                for filing_type in filing_types
            }
            query = query.where(
                Filing.filing_type.in_(normalized_types)
            )

        if limit is not None:
            query = query.limit(limit)

        filings_to_process = list(
            self.db.scalars(query).all()
        )

        total_filings = max(
            len(filings_to_process),
            1,
        )

        if progress_callback:
            progress_callback(
                0,
                total_filings,
                f"Discovered {len(new_filings)} new filing(s)",
            )

        processed_filings = []
        for index, filing in enumerate(
            filings_to_process,
            start=1,
        ):
            result = self.filing_ingestion_pipeline.ingest_filing(
                filing
            )
            processed_filings.append(result)

            if progress_callback:
                progress_callback(
                    index,
                    total_filings,
                    f"Indexed {filing.filing_type} {filing.accession_number}",
                )

        return CompanyIngestionResult(
            company_id=company.id,
            ticker=company.ticker,
            discovered_new_filings=len(new_filings),
            processed_filings=processed_filings,
        )

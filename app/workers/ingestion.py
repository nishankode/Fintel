import logging
from collections.abc import Callable

from redis import Redis
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.database import SessionLocal
from app.embeddings.service import EmbeddingService
from app.ingestion.chunking import FilingChunkingService
from app.ingestion.chunks import FilingChunkService
from app.ingestion.discovery import SECDiscoveryService
from app.ingestion.documents import FilingDocumentService
from app.ingestion.embeddings import ChunkEmbeddingService
from app.ingestion.jobs import IngestionJobService
from app.ingestion.parser import FilingParserService
from app.ingestion.persistence import SECFilingPersistenceService
from app.ingestion.pipeline import (
    CompanyIngestionPipeline,
    FilingIngestionPipeline,
)
from app.ingestion.queue import IngestionQueue
from app.integrations.sec.client import SECClient
from app.models import Company, IngestionJob
from app.storage.factory import build_document_storage


logger = logging.getLogger(__name__)


class IngestionWorker:
    def __init__(
        self,
        db_factory: Callable[[], Session],
        queue: IngestionQueue,
    ) -> None:
        self.db_factory = db_factory
        self.queue = queue

    def run_once(
        self,
        timeout_seconds: int = 5,
    ) -> bool:
        job_id = self.queue.dequeue(
            timeout_seconds=timeout_seconds,
        )

        if job_id is None:
            return False

        db = self.db_factory()

        try:
            self.process_job(
                db=db,
                job_id=job_id,
            )
            return True
        finally:
            db.close()

    def process_job(
        self,
        db: Session,
        job_id: int,
    ) -> None:
        job_service = IngestionJobService(db)
        job = job_service.get_job(job_id)

        if job is None:
            logger.warning(
                "Ingestion job not found: job_id=%s",
                job_id,
            )
            return

        if job.status == "completed":
            logger.info(
                "Ingestion job already completed: job_id=%s",
                job.id,
            )
            return

        job_service.mark_running(job)

        try:
            self._run_company_filings_job(
                db=db,
                job=job,
            )
            job_service.mark_completed(job)
        except Exception as error:
            job_service.mark_failed(
                job=job,
                error=error,
            )
            logger.exception(
                "Ingestion job failed: job_id=%s",
                job.id,
            )
            raise

    def _run_company_filings_job(
        self,
        db: Session,
        job: IngestionJob,
    ) -> None:
        company = db.get(
            Company,
            job.company_id,
        )

        if company is None:
            raise ValueError(
                f"Company not found for ingestion job: {job.company_id}"
            )

        payload = job.payload
        filing_types_payload = payload.get("filing_types")
        filing_types = (
            set(filing_types_payload)
            if filing_types_payload
            else None
        )

        settings = get_settings()
        sec_client = SECClient()

        try:
            storage = build_document_storage(settings)
            embedding_service = EmbeddingService(
                model_name=settings.embedding_model_name,
                expected_dimension=settings.embedding_dimension,
                device=settings.embedding_device,
            )
            discovery_service = SECDiscoveryService(
                client=sec_client,
            )
            filing_persistence_service = (
                SECFilingPersistenceService(
                    db=db,
                    discovery_service=discovery_service,
                )
            )
            filing_document_service = FilingDocumentService(
                db=db,
                sec_client=sec_client,
                storage=storage,
            )
            chunk_service = FilingChunkService(
                db=db,
                chunking_service=FilingChunkingService(),
            )
            filing_ingestion_pipeline = FilingIngestionPipeline(
                db=db,
                filing_document_service=filing_document_service,
                storage=storage,
                parser_service=FilingParserService(),
                chunk_service=chunk_service,
                chunk_embedding_service=ChunkEmbeddingService(
                    db=db,
                    embedding_service=embedding_service,
                ),
            )
            company_ingestion_pipeline = (
                CompanyIngestionPipeline(
                    db=db,
                    filing_persistence_service=(
                        filing_persistence_service
                    ),
                    filing_ingestion_pipeline=(
                        filing_ingestion_pipeline
                    ),
                )
            )

            company_ingestion_pipeline.ingest_company(
                company=company,
                filing_types=filing_types,
                limit=payload.get("limit"),
            )
        finally:
            sec_client.close()


def build_worker() -> IngestionWorker:
    settings = get_settings()
    redis_client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    queue = IngestionQueue(
        redis_client=redis_client,
        queue_name=settings.ingestion_queue_name,
    )

    return IngestionWorker(
        db_factory=SessionLocal,
        queue=queue,
    )


def run_forever() -> None:
    worker = build_worker()

    while True:
        worker.run_once()


if __name__ == "__main__":
    run_forever()

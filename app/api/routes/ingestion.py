import logging

from fastapi import APIRouter, HTTPException, status
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select

from app.auth import CurrentUserDependency
from app.core.settings import get_settings
from app.db.dependencies import DBDependency
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
from app.schemas.ingestion import (
    CompanyIngestionRequest,
    CompanyIngestionResponse,
)
from app.schemas.ingestion_job import IngestionJobResponse
from app.storage.factory import build_document_storage


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
)


@router.post(
    "/companies/{ticker}",
    status_code=status.HTTP_200_OK,
    response_model=CompanyIngestionResponse,
)
def ingest_company_filings(
    ticker: str,
    request: CompanyIngestionRequest,
    db: DBDependency,
    current_user: CurrentUserDependency,
):
    company = db.scalar(
        select(Company).where(
            Company.ticker == ticker.upper()
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
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
        chunking_service = FilingChunkingService()
        chunk_service = FilingChunkService(
            db=db,
            chunking_service=chunking_service,
        )
        chunk_embedding_service = ChunkEmbeddingService(
            db=db,
            embedding_service=embedding_service,
        )
        filing_ingestion_pipeline = FilingIngestionPipeline(
            db=db,
            filing_document_service=filing_document_service,
            storage=storage,
            parser_service=FilingParserService(),
            chunk_service=chunk_service,
            chunk_embedding_service=chunk_embedding_service,
        )
        company_ingestion_pipeline = CompanyIngestionPipeline(
            db=db,
            filing_persistence_service=filing_persistence_service,
            filing_ingestion_pipeline=filing_ingestion_pipeline,
        )

        result = company_ingestion_pipeline.ingest_company(
            company=company,
            filing_types=request.filing_types,
            filing_years=request.filing_years,
            limit=request.limit,
        )
    finally:
        sec_client.close()

    logger.info(
        "Company ingestion requested: ticker=%s user_id=%s processed=%s",
        company.ticker,
        current_user.id,
        len(result.processed_filings),
    )

    return result


@router.post(
    "/companies/{ticker}/jobs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestionJobResponse,
)
def enqueue_company_ingestion(
    ticker: str,
    request: CompanyIngestionRequest,
    db: DBDependency,
    current_user: CurrentUserDependency,
):
    company = db.scalar(
        select(Company).where(
            Company.ticker == ticker.upper()
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    settings = get_settings()
    job_service = IngestionJobService(db)
    job = job_service.create_company_filings_job(
        company=company,
        filing_types=request.filing_types,
        filing_years=request.filing_years,
        limit=request.limit,
    )
    redis_client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )
    queue = IngestionQueue(
        redis_client=redis_client,
        queue_name=settings.ingestion_queue_name,
    )

    try:
        queue.enqueue(job.id)
    except RedisError as error:
        job_service.mark_failed(
            job=job,
            error=error,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not enqueue ingestion job",
        ) from error
    finally:
        redis_client.close()

    logger.info(
        "Company ingestion job queued: ticker=%s job_id=%s user_id=%s",
        company.ticker,
        job.id,
        current_user.id,
    )

    return job


@router.get(
    "/jobs/{job_id}",
    status_code=status.HTTP_200_OK,
    response_model=IngestionJobResponse,
)
def get_ingestion_job(
    job_id: int,
    db: DBDependency,
    current_user: CurrentUserDependency,
):
    job = db.get(
        IngestionJob,
        job_id,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion job not found",
        )

    return job

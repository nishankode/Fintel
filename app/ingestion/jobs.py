from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, IngestionJob


class IngestionJobService:
    def __init__(
        self,
        db: Session,
    ) -> None:
        self.db = db

    def create_company_filings_job(
        self,
        company: Company,
        filing_types: set[str] | None = None,
        filing_years: set[int] | None = None,
        limit: int | None = None,
    ) -> IngestionJob:
        payload: dict[str, Any] = {
            "filing_types": (
                sorted(filing_types)
                if filing_types
                else None
            ),
            "filing_years": (
                sorted(filing_years)
                if filing_years
                else None
            ),
            "limit": limit,
        }
        job = IngestionJob(
            company_id=company.id,
            job_type="company_filings_ingestion",
            status="queued",
            payload=payload,
            progress_current=0,
            progress_total=1,
            progress_message="Queued for ingestion",
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        return job

    def get_job(
        self,
        job_id: int,
    ) -> IngestionJob | None:
        return self.db.scalar(
            select(IngestionJob).where(
                IngestionJob.id == job_id
            )
        )

    def mark_running(
        self,
        job: IngestionJob,
    ) -> None:
        job.status = "running"
        job.error_message = None
        job.progress_current = 0
        job.progress_total = max(
            job.progress_total,
            1,
        )
        job.progress_message = "Starting ingestion"
        self.db.commit()

    def mark_completed(
        self,
        job: IngestionJob,
    ) -> None:
        job.status = "completed"
        job.progress_total = max(
            job.progress_total,
            1,
        )
        job.progress_current = job.progress_total
        job.progress_message = "Ingestion completed"
        job.completed_at = datetime.now(UTC)
        self.db.commit()

    def mark_failed(
        self,
        job: IngestionJob,
        error: Exception,
    ) -> None:
        self.db.rollback()
        job.status = "failed"
        job.error_message = str(error)
        job.progress_message = "Ingestion failed"
        job.completed_at = datetime.now(UTC)
        self.db.commit()

    def update_progress(
        self,
        job: IngestionJob,
        current: int,
        total: int,
        message: str,
    ) -> None:
        job.progress_total = max(
            total,
            1,
        )
        job.progress_current = max(
            0,
            min(
                current,
                job.progress_total,
            ),
        )
        job.progress_message = message[:255]
        self.db.commit()

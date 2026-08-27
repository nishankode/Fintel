import unittest
from unittest.mock import Mock

from app.ingestion.jobs import IngestionJobService
from app.models import Company, IngestionJob


class IngestionJobServiceTests(unittest.TestCase):
    def test_creates_queued_company_filings_job(self):
        db = Mock()
        company = Company(
            id=10,
            cik="0000000010",
            ticker="ACME",
            name="Acme Inc.",
        )
        service = IngestionJobService(db)

        job = service.create_company_filings_job(
            company=company,
            filing_types={"10-Q", "10-K"},
            limit=2,
        )

        self.assertEqual(job.company_id, 10)
        self.assertEqual(job.status, "queued")
        self.assertEqual(job.progress_percent, 0)
        self.assertEqual(
            job.payload,
            {
                "filing_types": ["10-K", "10-Q"],
                "limit": 2,
            },
        )
        db.add.assert_called_once_with(job)
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(job)

    def test_updates_progress_for_running_job(self):
        db = Mock()
        service = IngestionJobService(db)
        job = IngestionJob(
            company_id=1,
            status="running",
            payload={},
        )

        service.update_progress(
            job=job,
            current=1,
            total=4,
            message="Indexed first filing",
        )

        self.assertEqual(job.progress_current, 1)
        self.assertEqual(job.progress_total, 4)
        self.assertEqual(job.progress_percent, 25)
        self.assertEqual(job.progress_message, "Indexed first filing")
        db.commit.assert_called_once()

    def test_marks_job_completed_at_100_percent(self):
        db = Mock()
        service = IngestionJobService(db)
        job = IngestionJob(
            company_id=1,
            status="running",
            payload={},
            progress_current=1,
            progress_total=3,
        )

        service.mark_completed(job)

        self.assertEqual(job.status, "completed")
        self.assertEqual(job.progress_current, 3)
        self.assertEqual(job.progress_total, 3)
        self.assertEqual(job.progress_percent, 100)
        self.assertEqual(job.progress_message, "Ingestion completed")
        self.assertIsNotNone(job.completed_at)
        db.commit.assert_called_once()

    def test_marks_job_failed_with_error_message(self):
        db = Mock()
        service = IngestionJobService(db)
        job = IngestionJob(
            company_id=1,
            status="running",
            payload={},
        )

        service.mark_failed(
            job=job,
            error=RuntimeError("boom"),
        )

        self.assertEqual(job.status, "failed")
        self.assertEqual(job.error_message, "boom")
        self.assertIsNotNone(job.completed_at)
        db.rollback.assert_called_once()
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()

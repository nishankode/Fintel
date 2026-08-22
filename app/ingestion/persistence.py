import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.discovery import SECDiscoveryService
from app.integrations.sec.urls import build_filing_document_url
from app.models import Company, Filing


logger = logging.getLogger(__name__)


class SECFilingPersistenceService:
    def __init__(
        self,
        db: Session,
        discovery_service: SECDiscoveryService,
    ) -> None:
        self.db = db
        self.discovery_service = discovery_service

    def sync_company_filings(
        self,
        company: Company,
        filing_types: set[str] | None = None,
    ) -> list[Filing]:

        discovered_filings = (
            self.discovery_service.get_recent_filings(
                cik=company.cik,
                filing_types=filing_types,
            )
        )

        if not discovered_filings:
            return []

        accession_numbers = [
            filing.accession_number
            for filing in discovered_filings
        ]

        existing_accession_numbers = set(
            self.db.scalars(
                select(Filing.accession_number).where(
                    Filing.accession_number.in_(
                        accession_numbers
                    )
                )
            ).all()
        )

        new_filings: list[Filing] = []

        for discovered_filing in discovered_filings:

            if (
                discovered_filing.accession_number
                in existing_accession_numbers
            ):
                continue

            source_url = build_filing_document_url(
                cik=company.cik,
                accession_number=(
                    discovered_filing.accession_number
                ),
                primary_document=(
                    discovered_filing.primary_document
                ),
            )

            filing = Filing(
                company_id=company.id,
                accession_number=(
                    discovered_filing.accession_number
                ),
                filing_type=(
                    discovered_filing.filing_type
                ),
                filed_at=discovered_filing.filed_at,
                reporting_period=(
                    discovered_filing.reporting_period
                ),
                source_url=source_url,
                status="pending",
            )

            self.db.add(filing)
            new_filings.append(filing)

        self.db.commit()

        for filing in new_filings:
            self.db.refresh(filing)

        logger.info(
            "SEC filing sync completed: company_id=%s discovered=%s new=%s",
            company.id,
            len(discovered_filings),
            len(new_filings),
        )

        return new_filings
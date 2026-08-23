import logging

from sqlalchemy.orm import Session

from app.integrations.sec.client import SECClient
from app.models import Filing
from app.storage.local import LocalDocumentStorage


logger = logging.getLogger(__name__)


class FilingDocumentService:
    def __init__(
        self,
        db: Session,
        sec_client: SECClient,
        storage: LocalDocumentStorage,
    ) -> None:
        self.db = db
        self.sec_client = sec_client
        self.storage = storage

    def download_and_store(
        self,
        filing: Filing,
    ) -> str:

        if (
            filing.storage_key
            and self.storage.exists(
                filing.storage_key
            )
        ):
            logger.info(
                "Filing document already stored: filing_id=%s",
                filing.id,
            )

            return filing.storage_key

        content = (
            self.sec_client.get_filing_document(
                filing.source_url
            )
        )

        storage_key = self.storage.save_filing(
            ticker=filing.company.ticker,
            accession_number=filing.accession_number,
            source_url=filing.source_url,
            content=content,
        )

        filing.storage_key = storage_key

        self.db.commit()
        self.db.refresh(filing)

        logger.info(
            "Filing document stored: filing_id=%s storage_key=%s",
            filing.id,
            storage_key,
        )

        return storage_key
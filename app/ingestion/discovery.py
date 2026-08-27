from datetime import date

from app.integrations.sec.client import SECClient
from app.integrations.sec.schemas import SECFilingMetadata


class SECDiscoveryService:

    def __init__(self, client: SECClient) -> None:
        self.client = client

    def get_recent_filings(
        self,
        cik: str,
        filing_types: set[str] | None = None
    ) -> list[SECFilingMetadata]:

        submissions = self.client.get_company_submissions(cik)

        recent = submissions["filings"]["recent"]

        accession_numbers = recent["accessionNumber"]
        forms = recent["form"]
        filing_dates = recent["filingDate"]
        report_dates = recent["reportDate"]
        primary_documents = recent["primaryDocument"]

        normalized_types = None

        if filing_types:
            normalized_types = {
                filing_type.upper()
                for filing_type in filing_types
            }

        filings: list[SECFilingMetadata] = []

        for index in range(len(accession_numbers)):
            filing_type = forms[index].upper()

            if (normalized_types is not None and filing_type not in normalized_types):
                continue

            report_date = (
                date.fromisoformat(report_dates[index])
                if report_dates[index]
                else None
            )

            filing = SECFilingMetadata(
                accession_number=accession_numbers[index],
                filing_type=filing_type,
                filed_at=date.fromisoformat(filing_dates[index]),
                reporting_period=report_date,
                primary_document=primary_documents[index]
            )

            filings.append(filing)

        return filings

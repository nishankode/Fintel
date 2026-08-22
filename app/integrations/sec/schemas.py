from datetime import date

from pydantic import BaseModel

class SECFilingMetadata(BaseModel):
    accession_number: str
    filing_type: str
    filed_at: date
    reporting_period: date | None
    primary_document: str
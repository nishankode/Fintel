from app.core.settings import get_settings


settings = get_settings()


def build_filing_document_url(
    cik: str,
    accession_number: str,
    primary_document: str,
) -> str:
    cik_without_leading_zeros = str(int(cik))

    accession_without_dashes = accession_number.replace("-", "")

    return (
        f"{settings.sec_base_url}/Archives/edgar/data/"
        f"{cik_without_leading_zeros}/"
        f"{accession_without_dashes}/"
        f"{primary_document}"
    )
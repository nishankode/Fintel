import httpx

from app.core.settings import get_settings


settings = get_settings()


class SECClient:
    def __init__(self) -> None:
        self.client = httpx.Client(
            headers={
                "User-Agent": settings.sec_user_agent,
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=30.0,
        )

    def get_company_submissions(
        self,
        cik: str,
    ) -> dict:
        normalized_cik = cik.zfill(10)

        url = (
            f"{settings.sec_data_base_url}"
            f"/submissions/CIK{normalized_cik}.json"
        )

        response = self.client.get(url)
        response.raise_for_status()

        return response.json()

    def get_filing_document(
        self,
        url: str,
    ) -> str:
        response = self.client.get(url)
        response.raise_for_status()

        return response.text

    def close(self) -> None:
        self.client.close()
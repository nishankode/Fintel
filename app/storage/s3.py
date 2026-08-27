from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError


class S3DocumentStorage:
    def __init__(
        self,
        bucket_name: str,
        key_prefix: str = "",
        endpoint_url: str | None = None,
        region_name: str | None = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.key_prefix = key_prefix.strip("/")
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
        )

    def save_filing(
        self,
        ticker: str,
        accession_number: str,
        source_url: str,
        content: str,
    ) -> str:
        storage_key = self._build_storage_key(
            ticker=ticker,
            accession_number=accession_number,
            source_url=source_url,
        )

        self.client.put_object(
            Bucket=self.bucket_name,
            Key=storage_key,
            Body=content.encode("utf-8"),
            ContentType="text/html; charset=utf-8",
        )

        return storage_key

    def read_text(
        self,
        storage_key: str,
    ) -> str:
        response = self.client.get_object(
            Bucket=self.bucket_name,
            Key=storage_key,
        )

        return response["Body"].read().decode("utf-8")

    def exists(
        self,
        storage_key: str,
    ) -> bool:
        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=storage_key,
            )
        except ClientError as error:
            status_code = (
                error.response.get("ResponseMetadata", {})
                .get("HTTPStatusCode")
            )

            if status_code == 404:
                return False

            raise

        return True

    def _build_storage_key(
        self,
        ticker: str,
        accession_number: str,
        source_url: str,
    ) -> str:
        filename = Path(
            urlparse(source_url).path
        ).name

        if not filename:
            raise ValueError(
                "Could not determine filing filename from source URL"
            )

        accession_without_dashes = (
            accession_number.replace("-", "")
        )

        key = (
            Path("filings")
            / ticker.upper()
            / accession_without_dashes
            / filename
        ).as_posix()

        if self.key_prefix:
            return f"{self.key_prefix}/{key}"

        return key

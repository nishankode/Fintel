from pathlib import Path
from urllib.parse import urlparse


class LocalDocumentStorage:
    def __init__(
        self,
        base_path: str,
    ) -> None:
        self.base_path = Path(base_path)

    def save_filing(
        self,
        ticker: str,
        accession_number: str,
        source_url: str,
        content: str,
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

        storage_key = (
            Path("filings")
            / ticker.upper()
            / accession_without_dashes
            / filename
        )

        full_path = self.base_path / storage_key

        full_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        full_path.write_text(
            content,
            encoding="utf-8",
        )

        return storage_key.as_posix()

    def read_text(
        self,
        storage_key: str,
    ) -> str:
        full_path = self.base_path / storage_key

        return full_path.read_text(
            encoding="utf-8",
        )

    def exists(
        self,
        storage_key: str,
    ) -> bool:
        return (
            self.base_path / storage_key
        ).exists()
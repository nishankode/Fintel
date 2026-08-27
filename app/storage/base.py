from typing import Protocol


class DocumentStorage(Protocol):
    def save_filing(
        self,
        ticker: str,
        accession_number: str,
        source_url: str,
        content: str,
    ) -> str:
        raise NotImplementedError

    def read_text(
        self,
        storage_key: str,
    ) -> str:
        raise NotImplementedError

    def exists(
        self,
        storage_key: str,
    ) -> bool:
        raise NotImplementedError

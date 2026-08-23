import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.chunking import FilingChunkingService
from app.ingestion.schemas import ParsedFilingDocument
from app.models import Chunk, Filing


logger = logging.getLogger(__name__)


class FilingChunkService:
    def __init__(
        self,
        db: Session,
        chunking_service: FilingChunkingService,
    ) -> None:
        self.db = db
        self.chunking_service = chunking_service

    def create_chunks(
        self,
        filing: Filing,
        document: ParsedFilingDocument,
    ) -> list[Chunk]:

        existing_chunks = self.db.scalars(
            select(Chunk)
            .where(
                Chunk.filing_id == filing.id
            )
            .order_by(
                Chunk.section_key,
                Chunk.chunk_index,
            )
        ).all()

        if existing_chunks:
            logger.info(
                "Filing already chunked: filing_id=%s chunks=%s",
                filing.id,
                len(existing_chunks),
            )

            return list(existing_chunks)

        prepared_chunks = (
            self.chunking_service.chunk_document(
                document
            )
        )

        chunks = [
            Chunk(
                filing_id=filing.id,
                section_key=prepared.section_key,
                chunk_index=prepared.chunk_index,
                text=prepared.text,
                character_count=prepared.character_count,
            )
            for prepared in prepared_chunks
        ]

        self.db.add_all(chunks)

        self.db.commit()

        logger.info(
            "Filing chunks persisted: filing_id=%s chunks=%s",
            filing.id,
            len(chunks),
        )

        return chunks
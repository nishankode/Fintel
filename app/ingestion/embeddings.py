import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.embeddings.service import EmbeddingService
from app.models import Chunk, Filing


logger = logging.getLogger(__name__)


class ChunkEmbeddingService:
    def __init__(
        self,
        db: Session,
        embedding_service: EmbeddingService,
        batch_size: int = 32,
    ) -> None:
        self.db = db
        self.embedding_service = embedding_service
        self.batch_size = batch_size

    def embed_filing_chunks(
        self,
        filing: Filing,
    ) -> int:
        total_chunks = self.db.scalar(
            select(func.count()).select_from(Chunk).where(
                Chunk.filing_id == filing.id,
            )
        )

        if total_chunks == 0:
            logger.info(
                "No chunks found for filing embedding: filing_id=%s",
                filing.id,
            )
            return 0

        chunks = list(
            self.db.scalars(
                select(Chunk)
                .where(
                    Chunk.filing_id == filing.id,
                    Chunk.embedding.is_(None),
                )
                .order_by(
                    Chunk.section_key,
                    Chunk.chunk_index,
                )
            ).all()
        )

        if not chunks:
            if filing.status != "indexed":
                filing.status = "indexed"
                self.db.commit()

            logger.info(
                "Filing chunks already embedded: filing_id=%s chunks=%s",
                filing.id,
                total_chunks,
            )
            return 0

        embedded_count = 0

        for start in range(
            0,
            len(chunks),
            self.batch_size,
        ):
            batch = chunks[
                start : start + self.batch_size
            ]

            texts = [
                chunk.text
                for chunk in batch
            ]

            embeddings = (
                self.embedding_service.embed_documents(
                    texts
                )
            )

            try:
                for chunk, embedding in zip(
                    batch,
                    embeddings,
                    strict=True,
                ):
                    chunk.embedding = embedding

                self.db.commit()
            except Exception:
                self.db.rollback()

                logger.exception(
                    "Embedding batch persistence failed: "
                    "filing_id=%s batch_start=%s batch_size=%s",
                    filing.id,
                    start,
                    len(batch),
                )

                raise

            embedded_count += len(batch)

            logger.info(
                "Embedding batch stored: "
                "filing_id=%s embedded=%s total=%s",
                filing.id,
                embedded_count,
                len(chunks),
            )

        filing.status = "indexed"
        self.db.commit()

        logger.info(
            "Filing embedding completed: "
            "filing_id=%s chunks=%s",
            filing.id,
            embedded_count,
        )

        return embedded_count

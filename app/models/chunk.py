from typing import TYPE_CHECKING

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.filing import Filing


class Chunk(Base):
    __tablename__ = "chunks"

    __table_args__ = (
        UniqueConstraint(
            "filing_id",
            "section_key",
            "chunk_index",
            name="uq_chunks_filing_section_index",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    filing_id: Mapped[int] = mapped_column(
        ForeignKey(
            "filings.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    section_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    character_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        VECTOR(384),
        nullable=True,
    )

    filing: Mapped["Filing"] = relationship(
        back_populates="chunks",
    )
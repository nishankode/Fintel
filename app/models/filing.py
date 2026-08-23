from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.chunk import Chunk
    from app.models.company import Company


class Filing(Base):
    __tablename__ = "filings"

    __table_args__ = (
        UniqueConstraint(
            "accession_number",
            name="uq_filings_accession_number",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey(
            "companies.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    accession_number: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    filing_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    filed_at: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    reporting_period: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    source_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
    )

    storage_key: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    company: Mapped["Company"] = relationship(
        back_populates="filings",
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="filing",
        cascade="all, delete-orphan",
    )
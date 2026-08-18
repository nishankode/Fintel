from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.filing import Filing


class Company(Base):

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    cik: Mapped[str] = mapped_column(
        String(10), 
        unique=True, 
        nullable=False, 
        index=True
    )

    ticker: Mapped[str] = mapped_column(
        String(10), 
        unique=True, 
        nullable=False, 
        index=True
    )

    name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )

    filings: Mapped[list["Filing"]] = relationship(
        back_populates='company',
        cascade="all, delete-orphan"
    )
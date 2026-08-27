"""add ingestion job progress

Revision ID: 2b4e6a19c8d2
Revises: 8efc31d7162a
Create Date: 2026-08-27 17:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "2b4e6a19c8d2"
down_revision: str | None = "8efc31d7162a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ingestion_jobs",
        sa.Column(
            "progress_current",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column(
            "progress_total",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "ingestion_jobs",
        sa.Column(
            "progress_message",
            sa.String(length=255),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "ingestion_jobs",
        "progress_message",
    )
    op.drop_column(
        "ingestion_jobs",
        "progress_total",
    )
    op.drop_column(
        "ingestion_jobs",
        "progress_current",
    )

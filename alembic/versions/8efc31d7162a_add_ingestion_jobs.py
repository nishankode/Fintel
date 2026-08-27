"""add ingestion jobs

Revision ID: 8efc31d7162a
Revises: 0fd641e0b4be
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8efc31d7162a"
down_revision: Union[str, Sequence[str], None] = "0fd641e0b4be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column(
            "job_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ingestion_jobs_company_id"),
        "ingestion_jobs",
        ["company_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ingestion_jobs_status"),
        "ingestion_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_ingestion_jobs_status_created_at",
        "ingestion_jobs",
        ["status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ingestion_jobs_status_created_at",
        table_name="ingestion_jobs",
    )
    op.drop_index(
        op.f("ix_ingestion_jobs_status"),
        table_name="ingestion_jobs",
    )
    op.drop_index(
        op.f("ix_ingestion_jobs_company_id"),
        table_name="ingestion_jobs",
    )
    op.drop_table("ingestion_jobs")

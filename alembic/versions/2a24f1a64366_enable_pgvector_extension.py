"""enable pgvector extension

Revision ID: 2a24f1a64366
Revises: ada29ad7a5f9
Create Date: 2026-08-23 11:16:28.047423

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a24f1a64366'
down_revision: Union[str, Sequence[str], None] = 'ada29ad7a5f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE EXTENSION IF NOT EXISTS vector"
    )


def downgrade() -> None:
    op.execute(
        "DROP EXTENSION IF EXISTS vector"
    )

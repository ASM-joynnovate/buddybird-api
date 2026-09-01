"""allow 128 character Firebase UIDs

Revision ID: 8c1f4e2a7b90
Revises: 6756160370ab
Create Date: 2026-09-01 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c1f4e2a7b90"
down_revision: str | Sequence[str] | None = "6756160370ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "audio_captures",
        "firebase_anon_uid",
        existing_type=sa.String(length=30),
        type_=sa.String(length=128),
        existing_nullable=False,
    )
    op.alter_column(
        "word_entries",
        "firebase_anon_uid",
        existing_type=sa.String(length=30),
        type_=sa.String(length=128),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "word_entries",
        "firebase_anon_uid",
        existing_type=sa.String(length=128),
        type_=sa.String(length=30),
        existing_nullable=True,
    )
    op.alter_column(
        "audio_captures",
        "firebase_anon_uid",
        existing_type=sa.String(length=128),
        type_=sa.String(length=30),
        existing_nullable=False,
    )

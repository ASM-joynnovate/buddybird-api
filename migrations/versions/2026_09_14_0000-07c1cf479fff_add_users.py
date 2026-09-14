"""add users

Revision ID: 07c1cf479fff
Revises: b5a24d1c8b64
Create Date: 2026-09-14 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "07c1cf479fff"
down_revision: str | Sequence[str] | None = "b5a24d1c8b64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("auth_user_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("nickname", sa.String(length=20), nullable=True),
        sa.Column("photo_file_id", sa.UUID(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version_id", sa.BigInteger(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["photo_file_id"], ["files.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("auth_user_id", name="uq_users_auth_user_id"),
        sa.UniqueConstraint("photo_file_id", name="uq_users_photo_file_id"),
    )
    op.create_index(
        "uq_users_nickname_active",
        "users",
        ["nickname"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_nickname_active", table_name="users")
    op.drop_table("users")

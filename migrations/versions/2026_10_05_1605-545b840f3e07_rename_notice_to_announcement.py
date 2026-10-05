"""rename notice to announcement

Revision ID: 545b840f3e07
Revises: f1cdec7f8237
Create Date: 2026-10-05 16:05:43.257689

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '545b840f3e07'
down_revision: Union[str, Sequence[str], None] = 'f1cdec7f8237'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table('notices', 'announcements')
    op.rename_table('notice_images', 'announcement_images')
    op.rename_table('notice_reads', 'announcement_reads')
    op.alter_column('announcement_images', 'notice_id', new_column_name='announcement_id')
    op.alter_column('announcement_reads', 'notice_id', new_column_name='announcement_id')
    op.alter_column('user_settings', 'notice_notification_enabled', new_column_name='announcement_notification_enabled')
    op.execute('ALTER TABLE announcements RENAME CONSTRAINT notices_pkey TO announcements_pkey')
    op.execute('ALTER TABLE announcements RENAME CONSTRAINT notices_title_i18n_id_fkey TO announcements_title_i18n_id_fkey')
    op.execute('ALTER TABLE announcements RENAME CONSTRAINT notices_body_i18n_id_fkey TO announcements_body_i18n_id_fkey')
    op.execute('ALTER TABLE announcements RENAME CONSTRAINT ck_notices_period TO ck_announcements_period')
    op.execute('ALTER INDEX ix_notices_starts_at RENAME TO ix_announcements_starts_at')
    op.execute('ALTER TABLE announcement_images RENAME CONSTRAINT notice_images_pkey TO announcement_images_pkey')
    op.execute('ALTER TABLE announcement_images RENAME CONSTRAINT notice_images_file_id_fkey TO announcement_images_file_id_fkey')
    op.execute('ALTER TABLE announcement_images RENAME CONSTRAINT notice_images_notice_id_fkey TO announcement_images_announcement_id_fkey')
    op.execute('ALTER TABLE announcement_images RENAME CONSTRAINT uq_notice_images_file_id TO uq_announcement_images_file_id')
    op.execute('ALTER TABLE announcement_images RENAME CONSTRAINT uq_notice_images_notice_id_display_order TO uq_announcement_images_announcement_id_display_order')
    op.execute('ALTER TABLE announcement_reads RENAME CONSTRAINT notice_reads_pkey TO announcement_reads_pkey')
    op.execute('ALTER TABLE announcement_reads RENAME CONSTRAINT notice_reads_notice_id_fkey TO announcement_reads_announcement_id_fkey')
    op.execute('ALTER TABLE announcement_reads RENAME CONSTRAINT notice_reads_user_id_fkey TO announcement_reads_user_id_fkey')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('ALTER TABLE announcement_reads RENAME CONSTRAINT announcement_reads_user_id_fkey TO notice_reads_user_id_fkey')
    op.execute('ALTER TABLE announcement_reads RENAME CONSTRAINT announcement_reads_announcement_id_fkey TO notice_reads_notice_id_fkey')
    op.execute('ALTER TABLE announcement_reads RENAME CONSTRAINT announcement_reads_pkey TO notice_reads_pkey')
    op.execute('ALTER TABLE announcement_images RENAME CONSTRAINT uq_announcement_images_announcement_id_display_order TO uq_notice_images_notice_id_display_order')
    op.execute('ALTER TABLE announcement_images RENAME CONSTRAINT uq_announcement_images_file_id TO uq_notice_images_file_id')
    op.execute('ALTER TABLE announcement_images RENAME CONSTRAINT announcement_images_announcement_id_fkey TO notice_images_notice_id_fkey')
    op.execute('ALTER TABLE announcement_images RENAME CONSTRAINT announcement_images_file_id_fkey TO notice_images_file_id_fkey')
    op.execute('ALTER TABLE announcement_images RENAME CONSTRAINT announcement_images_pkey TO notice_images_pkey')
    op.execute('ALTER INDEX ix_announcements_starts_at RENAME TO ix_notices_starts_at')
    op.execute('ALTER TABLE announcements RENAME CONSTRAINT ck_announcements_period TO ck_notices_period')
    op.execute('ALTER TABLE announcements RENAME CONSTRAINT announcements_body_i18n_id_fkey TO notices_body_i18n_id_fkey')
    op.execute('ALTER TABLE announcements RENAME CONSTRAINT announcements_title_i18n_id_fkey TO notices_title_i18n_id_fkey')
    op.execute('ALTER TABLE announcements RENAME CONSTRAINT announcements_pkey TO notices_pkey')
    op.alter_column('user_settings', 'announcement_notification_enabled', new_column_name='notice_notification_enabled')
    op.alter_column('announcement_reads', 'announcement_id', new_column_name='notice_id')
    op.alter_column('announcement_images', 'announcement_id', new_column_name='notice_id')
    op.rename_table('announcement_reads', 'notice_reads')
    op.rename_table('announcement_images', 'notice_images')
    op.rename_table('announcements', 'notices')

"""rename judgment tables and add mimic judgment status

Revision ID: 8b47198bded4
Revises: 3ac27c341441
Create Date: 2026-10-18 14:02:35.657520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b47198bded4'
down_revision: Union[str, Sequence[str], None] = '3ac27c341441'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table('sound_judgments', 'mimic_judgments')
    op.rename_table('sound_analyses', 'parrot_detections')
    op.execute('ALTER TABLE mimic_judgments RENAME CONSTRAINT sound_judgments_pkey TO mimic_judgments_pkey')
    op.execute('ALTER TABLE mimic_judgments RENAME CONSTRAINT sound_judgments_sound_id_fkey TO mimic_judgments_sound_id_fkey')
    op.execute('ALTER TABLE mimic_judgments RENAME CONSTRAINT sound_judgments_word_id_fkey TO mimic_judgments_word_id_fkey')
    op.execute('ALTER INDEX ix_sound_judgments_sound_id_judged_at RENAME TO ix_mimic_judgments_sound_id_judged_at')
    op.execute('ALTER TABLE parrot_detections RENAME CONSTRAINT sound_analyses_pkey TO parrot_detections_pkey')
    op.execute('ALTER TABLE parrot_detections RENAME CONSTRAINT sound_analyses_sound_id_fkey TO parrot_detections_sound_id_fkey')
    op.execute('ALTER TABLE parrot_detections RENAME CONSTRAINT uq_sound_analyses_sound_id_analyzer_version TO uq_parrot_detections_sound_id_analyzer_version')
    op.alter_column('session_sounds', 'judgment_status', new_column_name='parrot_detection_status')
    op.add_column('session_sounds', sa.Column('mimic_judgment_status', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('session_sounds', 'mimic_judgment_status')
    op.alter_column('session_sounds', 'parrot_detection_status', new_column_name='judgment_status')
    op.execute('ALTER TABLE parrot_detections RENAME CONSTRAINT uq_parrot_detections_sound_id_analyzer_version TO uq_sound_analyses_sound_id_analyzer_version')
    op.execute('ALTER TABLE parrot_detections RENAME CONSTRAINT parrot_detections_sound_id_fkey TO sound_analyses_sound_id_fkey')
    op.execute('ALTER TABLE parrot_detections RENAME CONSTRAINT parrot_detections_pkey TO sound_analyses_pkey')
    op.execute('ALTER INDEX ix_mimic_judgments_sound_id_judged_at RENAME TO ix_sound_judgments_sound_id_judged_at')
    op.execute('ALTER TABLE mimic_judgments RENAME CONSTRAINT mimic_judgments_word_id_fkey TO sound_judgments_word_id_fkey')
    op.execute('ALTER TABLE mimic_judgments RENAME CONSTRAINT mimic_judgments_sound_id_fkey TO sound_judgments_sound_id_fkey')
    op.execute('ALTER TABLE mimic_judgments RENAME CONSTRAINT mimic_judgments_pkey TO sound_judgments_pkey')
    op.rename_table('parrot_detections', 'sound_analyses')
    op.rename_table('mimic_judgments', 'sound_judgments')

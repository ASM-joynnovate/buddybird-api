"""rename parrot detection analyzer_version to model_version

Revision ID: dc7ede439f8b
Revises: 8b47198bded4
Create Date: 2026-10-18 18:15:07.957708

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dc7ede439f8b'
down_revision: Union[str, Sequence[str], None] = '8b47198bded4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('parrot_detections', 'analyzer_version', new_column_name='model_version')
    op.execute('ALTER TABLE parrot_detections RENAME CONSTRAINT uq_parrot_detections_sound_id_analyzer_version TO uq_parrot_detections_sound_id_model_version')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('ALTER TABLE parrot_detections RENAME CONSTRAINT uq_parrot_detections_sound_id_model_version TO uq_parrot_detections_sound_id_analyzer_version')
    op.alter_column('parrot_detections', 'model_version', new_column_name='analyzer_version')

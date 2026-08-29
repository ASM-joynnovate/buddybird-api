from sqlalchemy import UUID, Column, ForeignKey, PrimaryKeyConstraint, Table

from core.db.sqlalchemy.models.base import metadata

audio_capture_label_table = Table(
    "audio_capture_labels",
    metadata,
    Column("audio_capture_id", UUID, ForeignKey("audio_captures.id"), nullable=False),
    Column("label_option_id", UUID, ForeignKey("label_options.id"), nullable=False, index=True),
    PrimaryKeyConstraint("audio_capture_id", "label_option_id"),
)

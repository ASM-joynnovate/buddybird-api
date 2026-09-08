from sqlalchemy import UUID, Boolean, Column, ForeignKey, Integer, Text, false

from core.db.sqlalchemy.models.base import BaseTable, metadata
from core.db.sqlalchemy.models.file import file_table

audio_segment_table = BaseTable(
    "audio_segments",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("audio_capture_id", UUID, ForeignKey("legacy.audio_captures.id"), nullable=False, index=True),
    Column("start_ms", Integer, nullable=False),
    Column("end_ms", Integer, nullable=False),
    Column("audio_file_id", UUID, ForeignKey(file_table.c.id), nullable=False, index=True),
    Column("label_option_id", UUID, ForeignKey("legacy.label_options.id"), nullable=True, index=True),
    Column("memo", Text, nullable=True),
    Column("is_deleted", Boolean, nullable=False, default=False, server_default=false()),
    schema="legacy",
)

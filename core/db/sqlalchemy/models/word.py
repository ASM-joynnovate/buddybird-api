from uuid import uuid7

from sqlalchemy import UUID, Boolean, Column, ForeignKey, String, Text

from core.db.sqlalchemy.models.base import BaseTable, metadata

word_table = BaseTable(
    "word_entries",
    metadata,
    Column("id", UUID, primary_key=True, default=lambda: str(uuid7())),
    Column("label", String(255), nullable=False),
    Column("firebase_anon_uid", Text, nullable=False),
    Column("is_preset", Boolean, nullable=False),
    Column("audio_file_id", UUID, ForeignKey("files.id"), nullable=False),
    Column("device_platform", Text, nullable=True),
    Column("device_os_version", Text, nullable=True),
    Column("device_model", Text, nullable=True),
    Column("is_deleted", Boolean, nullable=False, default=False),
)

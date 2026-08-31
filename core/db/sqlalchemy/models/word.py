from sqlalchemy import UUID, Boolean, Column, ForeignKey, String, Text, false

from core.db.sqlalchemy.models.base import BaseTable, metadata

word_table = BaseTable(
    "word_entries",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("label", String(255), nullable=False),
    Column("firebase_anon_uid", String(128), nullable=True),
    Column("client_word_id", Text, nullable=False),
    Column("is_preset", Boolean, nullable=False, default=False, server_default=false()),
    Column("audio_file_id", UUID, ForeignKey("files.id"), nullable=False, index=True),
    Column("device_platform", String(10), nullable=True),
    Column("device_os_version", String(20), nullable=True),
    Column("device_model", String(30), nullable=True),
    Column("is_deleted", Boolean, nullable=False, default=False, server_default=false()),
)

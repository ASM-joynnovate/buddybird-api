from sqlalchemy import UUID, Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, false

from core.db.sqlalchemy.models.base import BaseTable, metadata

audio_capture_table = BaseTable(
    "audio_captures",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("firebase_anon_uid", Text, nullable=False),
    Column("client_capture_id", Text, nullable=False),
    Column("client_session_id", Text, nullable=False),
    Column("word_id", UUID, ForeignKey("word_entries.id"), nullable=True, index=True),
    Column("client_word_id", Text, nullable=False),
    Column("cycle", Integer, nullable=False),
    Column("phase", Text, nullable=False),
    Column("captured_at", DateTime(timezone=True), nullable=False),
    Column("duration_ms", Integer, nullable=True),
    Column("audio_file_id", UUID, ForeignKey("files.id"), nullable=False, index=True),
    Column("parrot_species", String(50), nullable=True),
    Column("parrot_birthdate", Date, nullable=True),
    Column("app_version", String(12), nullable=True),
    Column("device_platform", String(10), nullable=True),
    Column("device_os_version", String(20), nullable=True),
    Column("device_model", String(30), nullable=True),
    Column("memo", Text, nullable=True),
    Column("is_deleted", Boolean, nullable=False, default=False, server_default=false()),
)

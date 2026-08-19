from sqlalchemy import UUID, Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text

from core.db.sqlalchemy.models.base import BaseTable, metadata

audio_capture_table = BaseTable(
    "audio_captures",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("firebase_anon_uid", Text, nullable=False),
    Column("client_capture_id", Text, nullable=False),
    Column("client_session_id", Text, nullable=False),
    Column("word_id", ForeignKey("word_entries.id"), nullable=True),
    Column("client_word_id", Text, nullable=False),
    Column("cycle", Integer, nullable=False),
    Column("phase", Text, nullable=False),
    Column("captured_at", DateTime(timezone=True), nullable=False),
    Column("duration_ms", Integer, nullable=True),
    Column("audio_file_id", UUID, ForeignKey("files.id"), nullable=False),
    Column("parrot_species", String(50), nullable=True),
    Column("parrot_birthdate", Date, nullable=True),
    Column("app_version", Text, nullable=True),
    Column("device_platform", Text, nullable=True),
    Column("device_os_version", Text, nullable=True),
    Column("device_model", Text, nullable=True),
    Column("is_deleted", Boolean, nullable=False, default=False),
)

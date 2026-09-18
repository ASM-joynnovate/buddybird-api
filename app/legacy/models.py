from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid7

from sqlalchemy import (
    UUID as SQL_UUID,
)
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, File

LEGACY_TABLE_ARGS = {"schema": "legacy"}


class PhaseEnum(StrEnum):
    LEARNING = "LE"
    RESTING = "RE"


class LabelCategoryTargetEnum(StrEnum):
    CAPTURE = "CA"
    SEGMENT = "SE"


class LabelCategory(Base):
    __tablename__ = "label_categories"
    __table_args__ = LEGACY_TABLE_ARGS

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    target: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=LabelCategoryTargetEnum.SEGMENT.value,
        server_default=LabelCategoryTargetEnum.SEGMENT.value,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    options: Mapped[list[LabelOption]] = relationship(
        viewonly=True, lazy="selectin", order_by="LabelOption.display_order"
    )


class LabelOption(Base):
    __tablename__ = "label_options"
    __table_args__ = LEGACY_TABLE_ARGS

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    category_id: Mapped[UUID] = mapped_column(
        SQL_UUID, ForeignKey("legacy.label_categories.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class AudioCapture(Base):
    __tablename__ = "audio_captures"
    __table_args__ = LEGACY_TABLE_ARGS

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    firebase_anon_uid: Mapped[str] = mapped_column(Text, nullable=False)
    client_capture_id: Mapped[str] = mapped_column(Text, nullable=False)
    client_session_id: Mapped[str] = mapped_column(Text, nullable=False)
    word_id: Mapped[UUID | None] = mapped_column(
        SQL_UUID, ForeignKey("legacy.word_entries.id"), nullable=True, index=True
    )
    client_word_id: Mapped[str] = mapped_column(Text, nullable=False)
    cycle: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(Text, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audio_file_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=False, index=True)
    parrot_species: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parrot_birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(12), nullable=True)
    device_platform: Mapped[str | None] = mapped_column(String(10), nullable=True)
    device_os_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    device_model: Mapped[str | None] = mapped_column(String(30), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    audio_file: Mapped[File] = relationship(lazy="selectin")
    word: Mapped[Word | None] = relationship(lambda: Word, viewonly=True, lazy="selectin")
    label_options: Mapped[list[LabelOption]] = relationship(
        secondary=lambda: audio_capture_label_table, lazy="selectin"
    )


class AudioSegment(Base):
    __tablename__ = "audio_segments"
    __table_args__ = LEGACY_TABLE_ARGS

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    audio_capture_id: Mapped[UUID] = mapped_column(
        SQL_UUID, ForeignKey("legacy.audio_captures.id"), nullable=False, index=True
    )
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_file_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=False, index=True)
    label_option_id: Mapped[UUID | None] = mapped_column(
        SQL_UUID, ForeignKey("legacy.label_options.id"), nullable=True, index=True
    )
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    audio_file: Mapped[File] = relationship(lazy="selectin")


class Word(Base):
    __tablename__ = "word_entries"
    __table_args__ = LEGACY_TABLE_ARGS

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    firebase_anon_uid: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_word_id: Mapped[str] = mapped_column(Text, nullable=False)
    is_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    audio_file_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=False, index=True)
    device_platform: Mapped[str | None] = mapped_column(String(10), nullable=True)
    device_os_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    device_model: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    audio_file: Mapped[File] = relationship(lazy="selectin")


audio_capture_label_table = Table(
    "audio_capture_labels",
    Base.metadata,
    Column("audio_capture_id", SQL_UUID, ForeignKey("legacy.audio_captures.id"), nullable=False),
    Column("label_option_id", SQL_UUID, ForeignKey("legacy.label_options.id"), nullable=False, index=True),
    PrimaryKeyConstraint("audio_capture_id", "label_option_id"),
    schema="legacy",
)

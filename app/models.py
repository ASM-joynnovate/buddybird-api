from datetime import date, datetime, time
from typing import ClassVar
from uuid import UUID, uuid7

from sqlalchemy import (
    UUID as SQL_UUID,
)
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    false,
    func,
    text,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.enums import FileStatusEnum


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "pk": "%(table_name)s_pkey",
            "fk": "%(table_name)s_%(column_0_name)s_fkey",
        }
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now()
    )
    version_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")

    __mapper_args__: ClassVar[dict] = {"version_id_col": version_id}


class File(Base):
    __tablename__ = "files"

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    file_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=FileStatusEnum.UPLOADED.value, server_default=FileStatusEnum.UPLOADED.value
    )

    @property
    def object_key(self) -> str:
        return f"{self.file_path}/{self.file_name}"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("auth_user_id", name="uq_users_auth_user_id"),
        UniqueConstraint("photo_file_id", name="uq_users_photo_file_id"),
        Index(
            "uq_users_nickname_active",
            "nickname",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    auth_user_id: Mapped[UUID] = mapped_column(SQL_UUID, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(20), nullable=True)
    photo_file_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    photo_file: Mapped[File | None] = relationship(lazy="selectin")


class UserOAuthCredential(Base):
    __tablename__ = "user_oauth_credentials"
    __table_args__ = (CheckConstraint("provider IN ('google', 'apple')", name="ck_user_oauth_credentials_provider"),)

    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), primary_key=True)
    identity_id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True)
    client_id: Mapped[str] = mapped_column(Text, primary_key=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    credentials_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    proof_digest: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserWithdrawal(Base):
    __tablename__ = "user_withdrawals"
    __table_args__ = (
        CheckConstraint(
            "google_status IN ('not_required', 'pending', 'completed', 'unconfirmed')",
            name="ck_user_withdrawals_google_status",
        ),
        CheckConstraint(
            "apple_status IN ('not_required', 'pending', 'completed', 'unconfirmed')",
            name="ck_user_withdrawals_apple_status",
        ),
        CheckConstraint(
            "kakao_status IN ('not_required', 'pending', 'completed')", name="ck_user_withdrawals_kakao_status"
        ),
        CheckConstraint("attempt_count >= 0", name="ck_user_withdrawals_attempt_count"),
        CheckConstraint(
            "completed_at IS NULL OR next_attempt_at IS NULL", name="ck_user_withdrawals_completed_schedule"
        ),
        Index(
            "ix_user_withdrawals_next_attempt_at",
            "next_attempt_at",
            postgresql_where=text("completed_at IS NULL AND next_attempt_at IS NOT NULL"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), primary_key=True)
    google_status: Mapped[str] = mapped_column(Text, nullable=False)
    apple_status: Mapped[str] = mapped_column(Text, nullable=False)
    kakao_status: Mapped[str] = mapped_column(Text, nullable=False)
    kakao_user_ids_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserSetting(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), primary_key=True)
    sleep_at: Mapped[time] = mapped_column(Time, nullable=False, default=time(20, 0), server_default="20:00")
    wake_at: Mapped[time] = mapped_column(Time, nullable=False, default=time(8, 0), server_default="08:00")
    notify_emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    notify_mimicry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    notify_daily_summary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    notify_streak: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    notify_station_disconnect: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (
        UniqueConstraint("kind", "version", name="uq_consents_kind_version"),
        Index("ix_consents_kind_published_at", "kind", "published_at"),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class UserConsent(Base):
    __tablename__ = "user_consents"
    __table_args__ = (UniqueConstraint("user_id", "consent_id", name="uq_user_consents_user_id_consent_id"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), nullable=False)
    consent_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Consent.id), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consent: Mapped[Consent] = relationship(lazy="selectin")


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("user_id", "client_device_id", name="uq_devices_user_id_client_device_id"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), nullable=False)
    client_device_id: Mapped[UUID] = mapped_column(SQL_UUID, nullable=False)
    platform: Mapped[str] = mapped_column(String(10), nullable=False)
    os_version: Mapped[str] = mapped_column(String(20), nullable=False)
    model: Mapped[str] = mapped_column(String(30), nullable=False)
    app_version: Mapped[str] = mapped_column(String(12), nullable=False)
    push_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class PresetWord(Base):
    __tablename__ = "preset_words"
    __table_args__ = (UniqueConstraint("language", "name", name="uq_preset_words_language_name"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    language: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    audio_file_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class Word(Base):
    __tablename__ = "words"

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class WordRecording(Base):
    __tablename__ = "word_recordings"

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    word_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Word.id), index=True, nullable=False)
    file_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=False)
    file: Mapped[File] = relationship(lazy="selectin")
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint("status IN ('running', 'finished')", name="ck_sessions_status"),
        Index(
            "uq_sessions_user_running",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'running' AND is_deleted = false"),
        ),
        Index(
            "ix_sessions_last_heartbeat_at_running",
            "last_heartbeat_at",
            postgresql_where=text("status = 'running'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), index=True, nullable=False)
    station_device_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Device.id), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    word_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(Word.id), nullable=True)
    learning_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    settings_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    applied_settings_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    current_phase: Mapped[str | None] = mapped_column(Text, nullable=True)
    phase_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class SessionEvent(Base):
    __tablename__ = "session_events"
    __table_args__ = (Index("ix_session_events_session_id_occurred_at", "session_id", "occurred_at"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    session_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Session.id), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    word_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(Word.id), nullable=True)
    emergency_event_id: Mapped[UUID | None] = mapped_column(SQL_UUID, nullable=True)


class LearningDailySummary(Base):
    __tablename__ = "learning_daily_summary"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "word_id",
            "local_date",
            name="uq_learning_daily_summary_session_id_word_id_local_date",
        ),
        Index("ix_learning_daily_summary_word_id_local_date", "word_id", "local_date"),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    session_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Session.id), nullable=False)
    word_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Word.id), nullable=False)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    play_count: Mapped[int] = mapped_column(Integer, nullable=False)
    play_duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)


class ProcessedRequest(Base):
    __tablename__ = "processed_requests"
    __table_args__ = (UniqueConstraint("user_id", "request_id", name="uq_processed_requests_user_id_request_id"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), nullable=False)
    request_id: Mapped[UUID] = mapped_column(SQL_UUID, nullable=False)
    response_status: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    response_body: Mapped[str] = mapped_column(Text, nullable=False)


class Parrot(Base):
    __tablename__ = "parrots"
    __table_args__ = (UniqueConstraint("photo_file_id", name="uq_parrots_photo_file_id"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    photo_file_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    photo_file: Mapped[File | None] = relationship(lazy="selectin")


class SessionSound(Base):
    __tablename__ = "session_sounds"
    __table_args__ = (Index("ix_session_sounds_session_id_captured_at", "session_id", "captured_at"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    session_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Session.id), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    audio_file_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=False)
    audio_file: Mapped[File] = relationship(lazy="selectin")
    is_parrot_sound: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class SoundJudgment(Base):
    __tablename__ = "sound_judgments"
    __table_args__ = (Index("ix_sound_judgments_sound_id_judged_at", "sound_id", "judged_at"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    sound_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(SessionSound.id), nullable=False)
    word_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(Word.id), nullable=True)
    score: Mapped[float] = mapped_column(Double, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    judged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_id_sent_at", "user_id", "sent_at"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    emergency_event_id: Mapped[UUID | None] = mapped_column(SQL_UUID, nullable=True)
    image_file_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=True)
    image_file: Mapped[File | None] = relationship(lazy="selectin")
    sound_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(SessionSound.id), nullable=True)
    report_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = (Index("ix_feedbacks_created_at", "created_at"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), nullable=False)
    device_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Device.id), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    app_version: Mapped[str] = mapped_column(String(12), nullable=False)


class Notice(Base):
    __tablename__ = "notices"
    __table_args__ = (
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="ck_notices_period"),
        Index("ix_notices_starts_at", "starts_at"),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    images: Mapped[list[NoticeImage]] = relationship(lazy="selectin", order_by="NoticeImage.display_order")


class NoticeImage(Base):
    __tablename__ = "notice_images"
    __table_args__ = (
        UniqueConstraint("file_id", name="uq_notice_images_file_id"),
        UniqueConstraint("notice_id", "display_order", name="uq_notice_images_notice_id_display_order"),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    notice_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Notice.id), nullable=False)
    file_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=False)
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    file: Mapped[File] = relationship(lazy="selectin")


class NoticeRead(Base):
    __tablename__ = "notice_reads"

    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), primary_key=True)
    notice_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Notice.id), primary_key=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

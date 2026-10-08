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

from app.enums import FileStatusEnum, LocaleEnum, SoundJudgmentStatusEnum


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
        UniqueConstraint("uploading_photo_file_id", name="uq_users_uploading_photo_file_id"),
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
    uploading_photo_file_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    photo_file: Mapped[File | None] = relationship(lazy="selectin", foreign_keys=[photo_file_id])


class UserOAuthCredential(Base):
    __tablename__ = "user_oauth_credentials"
    __table_args__ = (CheckConstraint("provider IN ('google', 'apple')", name="ck_user_oauth_credentials_provider"),)

    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), primary_key=True)
    identity_id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True)
    client_id: Mapped[str] = mapped_column(Text, primary_key=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    credentials_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    proof_digest: Mapped[str | None] = mapped_column(Text, nullable=True)


class UserIdentity(Base):
    __tablename__ = "user_identities"

    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), primary_key=True)
    provider: Mapped[str] = mapped_column(Text, primary_key=True)


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


class UserWithdrawalFailure(Base):
    __tablename__ = "user_withdrawal_failures"

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), nullable=False)
    error_code: Mapped[str] = mapped_column(Text, nullable=False)


class UserSetting(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), primary_key=True)
    sleep_at: Mapped[time] = mapped_column(Time, nullable=False, default=time(20, 0), server_default="20:00")
    wake_at: Mapped[time] = mapped_column(Time, nullable=False, default=time(8, 0), server_default="08:00")
    push_notification_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    announcement_notification_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    report_notification_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    marketing_notification_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    marketing_night_notification_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )


class I18n(Base):
    __tablename__ = "i18n"

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    ko_kr: Mapped[str | None] = mapped_column(Text, nullable=True)
    en_us: Mapped[str] = mapped_column(Text, nullable=False)

    def get_text(self, locale: LocaleEnum) -> str:
        if locale == LocaleEnum.KO_KR and self.ko_kr is not None:
            return self.ko_kr

        return self.en_us


class Consent(Base):
    __tablename__ = "consents"
    __table_args__ = (
        UniqueConstraint("kind", "version", name="uq_consents_kind_version"),
        Index("ix_consents_kind_published_at", "kind", "published_at"),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title_i18n_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(I18n.id), nullable=False)
    body_i18n_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(I18n.id), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    title_i18n: Mapped[I18n] = relationship(lazy="selectin", foreign_keys=[title_i18n_id])
    body_i18n: Mapped[I18n] = relationship(lazy="selectin", foreign_keys=[body_i18n_id])


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
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    app_version: Mapped[str] = mapped_column(String(12), nullable=False)
    push_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str | None] = mapped_column(Text, nullable=True)
    locale: Mapped[str] = mapped_column(
        Text, nullable=False, default=LocaleEnum.EN_US.value, server_default=LocaleEnum.EN_US.value
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class PresetWord(Base):
    __tablename__ = "preset_words"
    __table_args__ = (
        Index(
            "uq_preset_words_language_name_active",
            "language",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    language: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    audio_file_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    audio_file: Mapped[File] = relationship(lazy="selectin")


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
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
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
    word_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Word.id), nullable=False)
    scheduled_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sleep_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    wake_at: Mapped[time | None] = mapped_column(Time, nullable=True)
    current_phase: Mapped[str | None] = mapped_column(Text, nullable=True)
    phase_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    ended_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    ended_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())


class SessionEvent(Base):
    __tablename__ = "session_events"
    __table_args__ = (
        Index("ix_session_events_session_id_occurred_at", "session_id", "occurred_at"),
        Index(
            "ix_session_events_occurred_at_emergency_detected",
            "occurred_at",
            postgresql_where=text("kind = 'emergency_detected'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    session_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Session.id), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    word_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(Word.id), nullable=True)
    emergency_event_id: Mapped[UUID | None] = mapped_column(SQL_UUID, nullable=True)


class LearningSegment(Base):
    __tablename__ = "learning_segments"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "word_id",
            "started_at",
            name="uq_learning_segments_session_id_word_id_started_at",
        ),
        Index("ix_learning_segments_word_id_started_at", "word_id", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    session_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Session.id), nullable=False)
    word_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Word.id), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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
    __table_args__ = (
        UniqueConstraint("photo_file_id", name="uq_parrots_photo_file_id"),
        UniqueConstraint("uploading_photo_file_id", name="uq_parrots_uploading_photo_file_id"),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    species: Mapped[str] = mapped_column(String(50), nullable=False)
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    photo_file_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=True)
    uploading_photo_file_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    photo_file: Mapped[File | None] = relationship(lazy="selectin", foreign_keys=[photo_file_id])


class SessionSound(Base):
    __tablename__ = "session_sounds"
    __table_args__ = (
        Index("ix_session_sounds_session_id_captured_at", "session_id", "captured_at"),
        Index(
            "ix_session_sounds_updated_at_failed",
            "updated_at",
            postgresql_where=text("judgment_status = 'failed'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    session_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Session.id), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    audio_file_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=False)
    audio_file: Mapped[File] = relationship(lazy="selectin")
    is_parrot_sound: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    judgment_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=SoundJudgmentStatusEnum.PENDING.value,
        server_default=SoundJudgmentStatusEnum.PENDING.value,
    )
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


class SoundAnalysis(Base):
    __tablename__ = "sound_analyses"
    __table_args__ = (
        UniqueConstraint("sound_id", "analyzer_version", name="uq_sound_analyses_sound_id_analyzer_version"),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    sound_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(SessionSound.id), nullable=False)
    analyzer_version: Mapped[str] = mapped_column(Text, nullable=False)
    is_parrot: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Double, nullable=False)
    call_count: Mapped[int] = mapped_column(Integer, nullable=False)
    chirp_count: Mapped[int] = mapped_column(Integer, nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SessionEventSound(Base):
    __tablename__ = "session_event_sounds"

    event_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(SessionEvent.id), primary_key=True)
    sound_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(SessionSound.id), primary_key=True)


class NotificationDispatch(Base):
    __tablename__ = "notification_dispatches"

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    title_i18n_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(I18n.id), nullable=False)
    body_i18n_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(I18n.id), nullable=False)
    image_file_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=True)
    image_file: Mapped[File | None] = relationship(lazy="selectin")
    target: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_local_datetime: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    title_i18n: Mapped[I18n] = relationship(lazy="selectin", foreign_keys=[title_i18n_id])
    body_i18n: Mapped[I18n] = relationship(lazy="selectin", foreign_keys=[body_i18n_id])


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_notifications_session_id"),
        Index("ix_notifications_user_id_sent_at", "user_id", "sent_at"),
        Index("ix_notifications_sent_at", "sent_at"),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    dispatch_id: Mapped[UUID | None] = mapped_column(
        SQL_UUID, ForeignKey(NotificationDispatch.id), index=True, nullable=True
    )
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    title_i18n_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(I18n.id), nullable=False)
    body_i18n_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(I18n.id), nullable=False)
    image_file_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=True)
    image_file: Mapped[File | None] = relationship(lazy="selectin")
    session_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(Session.id), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    title_i18n: Mapped[I18n] = relationship(lazy="selectin", foreign_keys=[title_i18n_id])
    body_i18n: Mapped[I18n] = relationship(lazy="selectin", foreign_keys=[body_i18n_id])


class Feedback(Base):
    __tablename__ = "feedbacks"
    __table_args__ = (Index("ix_feedbacks_created_at", "created_at"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), index=True, nullable=False)
    device_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Device.id), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    app_version: Mapped[str] = mapped_column(String(12), nullable=False)


class Announcement(Base):
    __tablename__ = "announcements"
    __table_args__ = (
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="ck_announcements_period"),
        Index("ix_announcements_starts_at", "starts_at"),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    title_i18n_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(I18n.id), nullable=False)
    body_i18n_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(I18n.id), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    push_local_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    push_prepared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    images: Mapped[list[AnnouncementImage]] = relationship(lazy="selectin", order_by="AnnouncementImage.display_order")
    title_i18n: Mapped[I18n] = relationship(lazy="selectin", foreign_keys=[title_i18n_id])
    body_i18n: Mapped[I18n | None] = relationship(lazy="selectin", foreign_keys=[body_i18n_id])


class AnnouncementImage(Base):
    __tablename__ = "announcement_images"
    __table_args__ = (
        UniqueConstraint("file_id", name="uq_announcement_images_file_id"),
        UniqueConstraint(
            "announcement_id", "display_order", name="uq_announcement_images_announcement_id_display_order"
        ),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    announcement_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Announcement.id), nullable=False)
    file_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(File.id), nullable=False)
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    file: Mapped[File] = relationship(lazy="selectin")


class AnnouncementRead(Base):
    __tablename__ = "announcement_reads"

    user_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(User.id), primary_key=True)
    announcement_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Announcement.id), primary_key=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PushDelivery(Base):
    __tablename__ = "push_deliveries"
    __table_args__ = (
        Index("ix_push_deliveries_device_id_sent_at", "device_id", "sent_at"),
        Index(
            "ix_push_deliveries_scheduled_at",
            "scheduled_at",
            postgresql_where=text("queued_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    device_id: Mapped[UUID] = mapped_column(SQL_UUID, ForeignKey(Device.id), nullable=False)
    notification_id: Mapped[UUID | None] = mapped_column(
        SQL_UUID, ForeignKey(Notification.id), index=True, nullable=True
    )
    announcement_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(Announcement.id), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppUpdate(Base):
    __tablename__ = "app_updates"
    __table_args__ = (UniqueConstraint("platform", "version", name="uq_app_updates_platform_version"),)

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(12), nullable=False)
    is_forced: Mapped[bool] = mapped_column(Boolean, nullable=False)
    release_notes_i18n_id: Mapped[UUID | None] = mapped_column(SQL_UUID, ForeignKey(I18n.id), nullable=True)
    release_notes_i18n: Mapped[I18n | None] = relationship(lazy="selectin")

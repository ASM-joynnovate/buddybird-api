from datetime import datetime
from enum import StrEnum
from typing import ClassVar
from uuid import UUID, uuid7

from sqlalchemy import (
    UUID as SQL_UUID,
)
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now(), server_default=func.now(), onupdate=func.now()
    )
    version_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")

    __mapper_args__: ClassVar[dict] = {"version_id_col": version_id}


class OAuthProviderEnum(StrEnum):
    GOOGLE = "google"
    APPLE = "apple"
    KAKAO = "kakao"


class WithdrawalStatusEnum(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    COMPLETED = "completed"
    UNCONFIRMED = "unconfirmed"


class File(Base):
    __tablename__ = "files"

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid7)
    file_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())

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
    data_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

from datetime import date, datetime
from typing import ClassVar
from uuid import UUID

from app.enums import (
    OAuthProviderEnum,
    WithdrawalProgressEnum,
    WithdrawalStatusEnum,
    WithdrawalStepEnum,
    WithdrawalStepStatusEnum,
)
from app.schemas.base import BaseResponse, CustomBaseModel, FileDTO, PageParams


class WithdrawalDTO(CustomBaseModel):
    user_id: UUID


class WithdrawalResponse(BaseResponse):
    data: WithdrawalDTO


class BackofficeWithdrawalProviderDTO(CustomBaseModel):
    provider: OAuthProviderEnum
    status: WithdrawalStatusEnum


class BackofficeWithdrawalDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"last_error_code", "next_attempt_at", "completed_at"}

    user_id: UUID
    providers: list[BackofficeWithdrawalProviderDTO]
    attempt_count: int
    last_error_code: str | None
    next_attempt_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class BackofficeWithdrawalStepDTO(CustomBaseModel):
    step: WithdrawalStepEnum
    status: WithdrawalStepStatusEnum


class BackofficeWithdrawalDeviceDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"last_seen_at"}

    platform: str
    app_version: str
    is_unsupported: bool
    last_seen_at: datetime | None


class BackofficeWithdrawalUserDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {
        "nickname",
        "email",
        "photo_file",
        "last_session_started_at",
        "last_seen_device",
        "last_feedback_message",
    }

    nickname: str | None
    email: str | None
    is_anonymous: bool
    photo_file: FileDTO | None
    created_at: datetime
    session_count: int
    last_session_started_at: datetime | None
    last_seen_device: BackofficeWithdrawalDeviceDTO | None
    device_count: int
    feedback_count: int
    last_feedback_message: str | None


class BackofficeWithdrawalListItemDTO(BackofficeWithdrawalDTO):
    status: WithdrawalProgressEnum
    steps: list[BackofficeWithdrawalStepDTO]
    user: BackofficeWithdrawalUserDTO


class BackofficeWithdrawalListResponse(BaseResponse):
    data: list[BackofficeWithdrawalListItemDTO]


class BackofficeWithdrawalListParams(PageParams):
    is_completed: bool | None = None
    created_from: date | None = None
    created_to: date | None = None

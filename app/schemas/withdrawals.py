from datetime import datetime
from typing import ClassVar
from uuid import UUID

from app.enums import OAuthProviderEnum, WithdrawalStatusEnum
from app.schemas.base import BaseResponse, CustomBaseModel, PageParams


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


class BackofficeWithdrawalListResponse(BaseResponse):
    data: list[BackofficeWithdrawalDTO]


class BackofficeWithdrawalListParams(PageParams):
    is_completed: bool | None = None

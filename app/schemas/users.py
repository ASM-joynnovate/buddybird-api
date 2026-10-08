import re
import unicodedata
from datetime import date, datetime
from typing import ClassVar
from uuid import UUID

from pydantic import Field, field_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.enums import (
    OAuthProviderEnum,
    PlatformEnum,
    SessionPhaseEnum,
    UserIssueEnum,
    UserLastSessionEnum,
    UserSortEnum,
)
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, FileDTO, PageParams
from app.schemas.devices import BackofficeDeviceDTO
from app.schemas.parrots import BackofficeParrotDTO
from app.schemas.settings import SettingsDTO
from app.schemas.withdrawals import BackofficeWithdrawalDTO


class UserDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"email", "nickname", "photo_file", "uploading_photo_file"}

    id: UUID
    email: str | None
    nickname: str | None
    photo_file: FileDTO | None
    uploading_photo_file: FileDTO | None


class UserResponse(BaseResponse):
    data: UserDTO


class BackofficeUserDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"email", "nickname"}

    id: UUID
    email: str | None
    nickname: str | None
    is_anonymous: bool
    is_deleted: bool
    created_at: datetime


class BackofficeUserParrotDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"photo_file"}

    name: str
    species: str
    photo_file: FileDTO | None


class BackofficeUserSessionDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"current_phase"}

    current_phase: SessionPhaseEnum | None


class BackofficeUserDeviceDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"last_seen_at"}

    platform: str
    app_version: str
    is_unsupported: bool
    last_seen_at: datetime | None


class BackofficeUserDailyDurationDTO(CustomBaseModel):
    date: date
    duration_ms: int


class BackofficeUserListItemDTO(BackofficeUserDTO):
    allow_null_fields: ClassVar[set] = {
        "email",
        "nickname",
        "photo_file",
        "first_parrot",
        "running_session",
        "last_seen_device",
    }

    photo_file: FileDTO | None
    first_parrot: BackofficeUserParrotDTO | None
    parrot_count: int
    running_session: BackofficeUserSessionDTO | None
    last_seen_device: BackofficeUserDeviceDTO | None
    device_count: int
    session_count: int
    daily_durations: list[BackofficeUserDailyDurationDTO]
    is_pushable: bool
    is_announcement_enabled: bool
    is_marketing_enabled: bool


class BackofficeUserDetailDTO(BackofficeUserDTO):
    allow_null_fields: ClassVar[set] = {"email", "nickname", "photo_file", "settings", "withdrawal"}

    photo_file: FileDTO | None
    providers: list[OAuthProviderEnum]
    settings: SettingsDTO | None
    parrots: list[BackofficeParrotDTO]
    devices: list[BackofficeDeviceDTO]
    withdrawal: BackofficeWithdrawalDTO | None


class BackofficeUserListResponse(BaseResponse):
    data: list[BackofficeUserListItemDTO]


class BackofficeUserDetailResponse(BaseResponse):
    data: BackofficeUserDetailDTO


class BackofficeUserListParams(PageParams):
    user_ids: list[UUID] | None = Field(None, min_length=1, max_length=100)
    keyword: str | None = Field(None, min_length=1, max_length=100)
    is_deleted: bool | None = None
    last_session: UserLastSessionEnum | None = None
    created_from: date | None = None
    created_to: date | None = None
    provider: OAuthProviderEnum | None = None
    is_anonymous: bool | None = None
    platform: PlatformEnum | None = None
    has_unsupported_device: bool | None = None
    is_pushable: bool | None = None
    is_marketing_enabled: bool | None = None
    issue: UserIssueEnum | None = None
    sort: UserSortEnum = UserSortEnum.CREATED_AT


class UpdateUserRequest(BaseRequest):
    null_fields: ClassVar[set] = {"nickname"}

    nickname: str | MISSING | None = MISSING

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str | MISSING | None) -> str | MISSING | None:
        if not isinstance(value, str):
            return value

        value = unicodedata.normalize("NFC", value).strip(" ")

        if not value or not 2 <= len(value) <= 20 or re.fullmatch(r"[ㄱ-ㅎㅏ-ㅣ가-힣A-Za-z0-9_ ]+", value) is None:
            raise ValueError("닉네임은 한글, 영문, 숫자, 밑줄, 공백으로 구성된 2~20자여야 합니다.")

        return value

import re
import unicodedata
from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import Field, field_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, FileDTO, PageParams
from app.schemas.devices import DeviceDTO
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


class BackofficeUserDetailDTO(BackofficeUserDTO):
    allow_null_fields: ClassVar[set] = {"email", "nickname", "photo_file", "settings", "withdrawal"}

    photo_file: FileDTO | None
    settings: SettingsDTO | None
    devices: list[DeviceDTO]
    withdrawal: BackofficeWithdrawalDTO | None


class BackofficeUserListResponse(BaseResponse):
    data: list[BackofficeUserDTO]


class BackofficeUserDetailResponse(BaseResponse):
    data: BackofficeUserDetailDTO


class BackofficeUserListParams(PageParams):
    keyword: str | None = Field(None, min_length=1, max_length=100)
    is_deleted: bool | None = None


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

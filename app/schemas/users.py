import re
import unicodedata
from typing import ClassVar
from uuid import UUID

from pydantic import field_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class ProfilePhotoDTO(CustomBaseModel):
    url: str


class UserDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"email", "nickname", "photo"}

    id: UUID
    email: str | None
    nickname: str | None
    photo: ProfilePhotoDTO | None


class UserResponse(BaseResponse):
    data: UserDTO


class UpdateUserRequest(BaseRequest):
    null_fields: ClassVar[set] = {"nickname"}

    nickname: str | MISSING | None = MISSING

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str | MISSING | None) -> str | MISSING | None:
        if not isinstance(value, str):
            return value

        value = unicodedata.normalize("NFC", value).strip(" ")

        if not value or not 2 <= len(value) <= 20 or re.fullmatch(r"[가-힣A-Za-z0-9_ ]+", value) is None:
            raise ValueError("닉네임은 한글, 영문, 숫자, 밑줄, 공백으로 구성된 2~20자여야 합니다.")

        return value

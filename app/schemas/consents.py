from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import AwareDatetime, field_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.enums import ConsentStatusEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class ConsentDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"status"}

    id: UUID
    kind: str
    version: int
    title: str
    body: str
    is_required: bool
    published_at: datetime
    status: ConsentStatusEnum | None


class ConsentResponse(BaseResponse):
    data: ConsentDTO


class ConsentListResponse(BaseResponse):
    data: list[ConsentDTO]


class CreateConsentRequest(BaseRequest):
    kind: str
    title: str
    body: str
    is_required: bool
    published_at: AwareDatetime

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        value = value.strip()

        if not 1 <= len(value) <= 50:
            raise ValueError("동의 종류는 1~50자여야 합니다.")

        return value

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()

        if not 1 <= len(value) <= 100:
            raise ValueError("제목은 1~100자여야 합니다.")

        return value

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        value = value.strip()

        if len(value) == 0:
            raise ValueError("본문을 입력해 주세요.")

        return value


class UpdateConsentRequest(BaseRequest):
    title: str | MISSING = MISSING
    body: str | MISSING = MISSING
    is_required: bool | MISSING = MISSING
    published_at: AwareDatetime | MISSING = MISSING

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | MISSING) -> str | MISSING:
        if not isinstance(value, str):
            return value

        value = value.strip()

        if not 1 <= len(value) <= 100:
            raise ValueError("제목은 1~100자여야 합니다.")

        return value

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str | MISSING) -> str | MISSING:
        if not isinstance(value, str):
            return value

        value = value.strip()

        if len(value) == 0:
            raise ValueError("본문을 입력해 주세요.")

        return value


class UserConsentDTO(CustomBaseModel):
    consent_id: UUID
    kind: str
    version: int
    status: ConsentStatusEnum
    decided_at: datetime


class UserConsentResponse(BaseResponse):
    data: UserConsentDTO


class UserConsentListResponse(BaseResponse):
    data: list[UserConsentDTO]


class SaveUserConsentRequest(BaseRequest):
    consent_id: UUID
    status: ConsentStatusEnum

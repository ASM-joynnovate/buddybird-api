from datetime import UTC, date, datetime
from typing import ClassVar
from uuid import UUID

from pydantic import field_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class ParrotPhotoDTO(CustomBaseModel):
    url: str


class ParrotDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"birthdate", "photo"}

    id: UUID
    name: str
    species: str
    birthdate: date | None
    photo: ParrotPhotoDTO | None


class ParrotResponse(BaseResponse):
    data: ParrotDTO


class ParrotListResponse(BaseResponse):
    data: list[ParrotDTO]


class CreateParrotRequest(BaseRequest):
    null_fields: ClassVar[set] = {"birthdate"}

    name: str
    species: str
    birthdate: date | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not 1 <= len(value) <= 20:
            raise ValueError("이름은 1~20자여야 합니다.")

        return value

    @field_validator("species")
    @classmethod
    def validate_species(cls, value: str) -> str:
        value = value.strip()

        if not 1 <= len(value) <= 50:
            raise ValueError("종은 1~50자여야 합니다.")

        return value

    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, value: date | None) -> date | None:
        if value is not None and value > datetime.now(UTC).date():
            raise ValueError("생일은 오늘 이전이어야 합니다.")

        return value


class UpdateParrotRequest(BaseRequest):
    null_fields: ClassVar[set] = {"birthdate"}

    name: str | MISSING = MISSING
    species: str | MISSING = MISSING
    birthdate: date | MISSING | None = MISSING

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | MISSING) -> str | MISSING:
        if not isinstance(value, str):
            return value

        value = value.strip()

        if not 1 <= len(value) <= 20:
            raise ValueError("이름은 1~20자여야 합니다.")

        return value

    @field_validator("species")
    @classmethod
    def validate_species(cls, value: str | MISSING) -> str | MISSING:
        if not isinstance(value, str):
            return value

        value = value.strip()

        if not 1 <= len(value) <= 50:
            raise ValueError("종은 1~50자여야 합니다.")

        return value

    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, value: date | MISSING | None) -> date | MISSING | None:
        if isinstance(value, date) and value > datetime.now(UTC).date():
            raise ValueError("생일은 오늘 이전이어야 합니다.")

        return value

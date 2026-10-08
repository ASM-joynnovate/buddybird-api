from datetime import UTC, date, datetime
from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import StringConstraints, field_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, FileDTO

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
Species = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class ParrotDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"birthdate", "photo_file", "uploading_photo_file"}

    id: UUID
    name: str
    species: str
    birthdate: date | None
    photo_file: FileDTO | None
    uploading_photo_file: FileDTO | None


class ParrotResponse(BaseResponse):
    data: ParrotDTO


class ParrotListResponse(BaseResponse):
    data: list[ParrotDTO]


class BackofficeParrotDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"birthdate", "photo_file"}

    id: UUID
    name: str
    species: str
    birthdate: date | None
    photo_file: FileDTO | None
    created_at: datetime


class CreateParrotRequest(BaseRequest):
    null_fields: ClassVar[set] = {"birthdate"}

    name: Name
    species: Species
    birthdate: date | None = None

    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, value: date | None) -> date | None:
        if value is not None and value > datetime.now(UTC).date():
            raise ValueError("생일은 오늘 이전이어야 합니다.")

        return value


class UpdateParrotRequest(BaseRequest):
    null_fields: ClassVar[set] = {"birthdate"}

    name: Name | MISSING = MISSING
    species: Species | MISSING = MISSING
    birthdate: date | MISSING | None = MISSING

    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, value: date | MISSING | None) -> date | MISSING | None:
        if isinstance(value, date) and value > datetime.now(UTC).date():
            raise ValueError("생일은 오늘 이전이어야 합니다.")

        return value

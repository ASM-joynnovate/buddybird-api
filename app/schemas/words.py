from datetime import datetime
from uuid import UUID

from pydantic import field_validator

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class WordRecordingDTO(CustomBaseModel):
    id: UUID
    url: str
    created_at: datetime


class WordDTO(CustomBaseModel):
    id: UUID
    name: str
    recordings: list[WordRecordingDTO]


class WordResponse(BaseResponse):
    data: WordDTO


class WordListResponse(BaseResponse):
    data: list[WordDTO]


class SaveWordRequest(BaseRequest):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not 1 <= len(value) <= 50:
            raise ValueError("단어 이름은 1~50자여야 합니다.")

        return value

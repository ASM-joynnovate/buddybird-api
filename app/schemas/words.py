from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import StringConstraints

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
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]

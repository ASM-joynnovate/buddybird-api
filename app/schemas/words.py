from datetime import datetime
from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import Field, StringConstraints

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, FileDTO, UploadDTO, UploadRequest


class WordRecordingDTO(CustomBaseModel):
    id: UUID
    audio_file: FileDTO
    display_order: int
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


class WordRecordingUploadRequest(UploadRequest):
    null_fields: ClassVar[set] = {"display_order"}

    display_order: int | None = Field(None, ge=0, le=32767)


class WordRecordingUploadDTO(UploadDTO):
    recording_id: UUID


class WordRecordingUploadResponse(BaseResponse):
    data: WordRecordingUploadDTO

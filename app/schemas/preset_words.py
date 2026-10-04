from typing import Annotated
from uuid import UUID

from fastapi import File, UploadFile
from pydantic import StringConstraints

from app.enums import PresetLanguageEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, FileDTO


class PresetWordDTO(CustomBaseModel):
    id: UUID
    language: PresetLanguageEnum
    name: str
    audio_file: FileDTO


class PresetWordResponse(BaseResponse):
    data: PresetWordDTO


class PresetWordListResponse(BaseResponse):
    data: list[PresetWordDTO]


class CreatePresetWordRequest(BaseRequest):
    language: PresetLanguageEnum
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
    file: Annotated[UploadFile, File()]


class UpdatePresetWordRequest(BaseRequest):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)] | None = None
    file: Annotated[UploadFile | None, File()] = None

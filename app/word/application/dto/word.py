from typing import ClassVar
from uuid import UUID

from pydantic import Field

from app.shared_kernel.application.dto import CreateFileDTO
from core.common import CustomBaseModel


class GetWordDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"firebase_anon_uid", "device_platform", "device_os_version", "device_model"}

    id: UUID = Field(..., description="ID")
    label: str = Field(..., description="단어명")
    firebase_anon_uid: str | None = Field(None, max_length=128, description="Firebase Authentication 익명 ID")
    client_word_id: str = Field(..., description="클라이언드 단어 ID")
    device_platform: str | None = Field(None, description="단어를 녹음한 기기의 OS")
    device_os_version: str | None = Field(None, description="단어를 녹음한 기기의 OS 버전")
    device_model: str | None = Field(None, description="단어를 녹음한 기기의 모델명")


class CreateWordDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"device_platform", "device_os_version", "device_model"}

    label: str = Field(..., min_length=1, max_length=100, description="단어명")
    firebase_anon_uid: str = Field(..., min_length=1, max_length=128, description="Firebase Authentication 익명 ID")
    client_word_id: str = Field(..., description="클라이언드 단어 ID")
    audio_file: CreateFileDTO = Field(..., description="단어 오디오 파일")
    device_platform: str | None = Field(None, max_length=10, description="단어를 녹음한 기기의 OS")
    device_os_version: str | None = Field(None, max_length=20, description="단어를 녹음한 기기의 OS 버전")
    device_model: str | None = Field(None, max_length=30, description="단어를 녹음한 기기의 모델명")

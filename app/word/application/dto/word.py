from uuid import UUID

from pydantic import Field

from app.shared_kernel.application.dto.file import CreateFileDTO
from core.common import CustomBaseModel


class GetWordDTO(CustomBaseModel):
    id: UUID = Field(..., description="ID")
    label: str = Field(..., description="단어명")
    firebase_anon_uid: str = Field(..., description="Firebase Authentication 익명 ID")
    device_platform: str | None = Field(None, description="단어를 녹음한 기기의 OS")
    device_os_version: str | None = Field(None, description="단어를 녹음한 기기의 OS 버전")
    device_model: str | None = Field(None, description="단어를 녹음한 기기의 모델명")


class CreateWordDTO(CustomBaseModel):
    label: str = Field(..., min_length=1, max_length=100, description="단어명")
    firebase_anon_uid: str = Field(..., min_length=1, max_length=128, description="Firebase Authentication 익명 ID")
    audio_file: CreateFileDTO = Field(..., description="단어 오디오 파일")
    device_platform: str | None = Field(None, max_length=200, description="단어를 녹음한 기기의 OS")
    device_os_version: str | None = Field(None, max_length=200, description="단어를 녹음한 기기의 OS 버전")
    device_model: str | None = Field(None, max_length=200, description="단어를 녹음한 기기의 모델명")
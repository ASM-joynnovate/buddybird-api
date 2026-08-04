from typing import Annotated, Any

from fastapi import File, UploadFile
from pydantic import BaseModel, ConfigDict, Field, Json, field_validator

from app.audio_capture.application.dto.audio_capture import CreateAudioCaptureItemDTO
from app.audio_capture.presentation.rest.v1.exceptions import AudioCaptureBatchSizeExceededException
from app.shared_kernel.domain.exceptions import FileSizeExceededException
from core.helpers.utils import FileSizeHelper

MAX_BATCH_SIZE = 10
MAX_ARCHIVE_SIZE = "10MB"


def as_json_text(schema: dict[str, Any]) -> None:
    schema.pop("contentMediaType", None)


class BatchCreateAudioCaptureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    firebase_anon_uid: str = Field(
        ..., max_length=30, description="Firebase Authentication UID", examples=["FJTNzziLv9VlWUaOMUUdrWNe3Rm2"]
    )
    metadata: Json[list[CreateAudioCaptureItemDTO]] = Field(
        ...,
        description="클립 메타 항목을 담은 JSON 배열",
        json_schema_extra=as_json_text,
        examples=[
            '[{"client_capture_id":"cap_20260804_01","client_session_id":"ses_20260804_01",'
            '"client_word_id":"preset-hello","cycle":1,"phase":"LE",'
            '"captured_at":"2026-08-04T01:00:00Z","file_name":"archive_10/01.wav",'
            '"app_version":"1.0.0","parrot_species":"왕관앵무","parrot_birthdate":"2024-03-15"}]'
        ],
    )
    file: Annotated[UploadFile, File(..., description="클립 오디오를 담은 압축 파일")]
    device_platform: str | None = Field(None, max_length=10, description="클립을 캡처한 기기의 OS")
    device_os_version: str | None = Field(None, max_length=20, description="클립을 캡처한 기기의 OS 버전")
    device_model: str | None = Field(None, max_length=30, description="클립을 캡처한 기기의 모델명")

    @field_validator("metadata")
    @classmethod
    def within_batch_size(cls, value: list[CreateAudioCaptureItemDTO]) -> list[CreateAudioCaptureItemDTO]:
        if len(value) > MAX_BATCH_SIZE:
            raise AudioCaptureBatchSizeExceededException
        return value

    @field_validator("file")
    @classmethod
    def within_archive_size(cls, value: UploadFile) -> UploadFile:
        if value.size is not None and value.size > FileSizeHelper.convert_size_to_bytes(MAX_ARCHIVE_SIZE):
            raise FileSizeExceededException(
                message=f"압축 파일의 최대 크기를 초과했습니다. 최대 크기: {MAX_ARCHIVE_SIZE}"
            )
        return value

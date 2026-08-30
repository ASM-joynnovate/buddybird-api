from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import File, UploadFile
from pydantic import BaseModel, ConfigDict, Field, Json, field_validator

from app.audio_capture.application.dto.audio_capture import CreateAudioCaptureItemDTO
from app.audio_capture.presentation.rest.v1.errors import AudioCaptureBatchSizeExceededError
from app.shared_kernel.domain.errors import FileSizeExceededError
from core.common.request.base import PageParams
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
            raise AudioCaptureBatchSizeExceededError
        return value

    @field_validator("file")
    @classmethod
    def within_archive_size(cls, value: UploadFile) -> UploadFile:
        if value.size is not None and value.size > FileSizeHelper.convert_size_to_bytes(MAX_ARCHIVE_SIZE):
            raise FileSizeExceededError(message=f"압축 파일의 최대 크기를 초과했습니다. 최대 크기: {MAX_ARCHIVE_SIZE}")
        return value


class GetAudioCaptureListRequest(PageParams):
    firebase_anon_uid: str | None = Field(None, description="Firebase Authentication 익명 ID")
    word_label: str | None = Field(None, description="연결된 단어명")
    label_option_ids: list[UUID] = Field([], description="클립 라벨 옵션 ID 필터")
    has_memo: bool | None = Field(None, description="메모가 있는 세그먼트 존재 여부 필터")
    date_from: datetime | None = Field(None, description="캡처 시각 시작 범위")
    date_to: datetime | None = Field(None, description="캡처 시각 끝 범위")


class AssignAudioCaptureLabelsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label_option_ids: list[UUID] = Field(..., description="지정할 라벨 옵션 ID 목록", examples=[[]])


class MigrateReviewLabelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str = Field(..., description="라벨 카테고리 이름", examples=["새 소리"])
    option: str = Field(..., description="라벨 옵션 이름", examples=["참새"])


class MigrateReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audio_file_id: str = Field(
        ...,
        description="S3 object key",
        examples=["audio_capture/{uid}/{capture_id}/{file_id}/session-xxx.wav"],
    )
    label: list[MigrateReviewLabelRequest] = Field(..., description="라벨 목록", examples=[[]])
    memo: str = Field(..., description="메모 내용", examples=[""])

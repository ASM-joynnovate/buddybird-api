from datetime import date, datetime
from typing import Annotated, Any, ClassVar
from uuid import UUID

from fastapi import File, UploadFile
from pydantic import Field, Json, field_validator

from app.audio_capture.domain.constants import MAX_ARCHIVE_SIZE, MAX_BATCH_SIZE
from app.audio_capture.domain.enums import PhaseEnum
from core.common.request import BaseRequest, PageParams
from core.helpers.utils import convert_size_to_bytes


def as_json_text(schema: dict[str, Any]) -> None:
    schema.pop("contentMediaType", None)


class CreateAudioCaptureItemRequest(BaseRequest):
    null_fields: ClassVar[set] = {"app_version", "parrot_species", "parrot_birthdate"}

    client_capture_id: str = Field(
        ...,
        max_length=50,
        description="클라이언트가 부여한 클립 ID",
        examples=["cap_20260804_01"],
    )
    client_session_id: str = Field(
        ...,
        max_length=30,
        description="클립을 캡처한 세션 ID",
        examples=["ses_20260804_01"],
    )
    client_word_id: str = Field(
        ...,
        max_length=50,
        description="클립이 가리키는 단어의 클라이언트 ID",
        examples=["preset-hello"],
    )
    cycle: int = Field(..., description="세션의 사이클 번호", examples=[1])
    phase: PhaseEnum = Field(..., description="클립을 캡처한 세션 구간", examples=[PhaseEnum.LEARNING])
    captured_at: datetime = Field(
        ..., description="클라이언트에서 클립을 캡처한 시각", examples=["2026-08-04T01:00:00Z"]
    )
    file_name: str = Field(
        ...,
        max_length=255,
        description="압축 파일 안에서 이 클립의 오디오를 가리키는 이름",
        examples=["archive_10/01.wav"],
    )
    app_version: str | None = Field(None, max_length=12, description="클립을 캡처한 앱 버전", examples=["1.0.0"])
    parrot_species: str | None = Field(None, max_length=50, description="앵무새 종", examples=["왕관앵무"])
    parrot_birthdate: date | None = Field(None, description="앵무새 생년월일", examples=["2024-03-15"])


class BatchCreateAudioCaptureRequest(BaseRequest):
    null_fields: ClassVar[set] = {"device_platform", "device_os_version", "device_model"}

    firebase_anon_uid: str = Field(
        ..., max_length=128, description="Firebase Authentication UID", examples=["FJTNzziLv9VlWUaOMUUdrWNe3Rm2"]
    )
    metadata: Json[list[CreateAudioCaptureItemRequest]] = Field(
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
    file: Annotated[
        UploadFile,
        File(..., description="클립 오디오를 담은 압축 파일", examples=["audio-captures.zip"]),
    ]
    device_platform: str | None = Field(None, max_length=10, description="클립을 캡처한 기기의 OS", examples=["iOS"])
    device_os_version: str | None = Field(
        None, max_length=20, description="클립을 캡처한 기기의 OS 버전", examples=["18.6"]
    )
    device_model: str | None = Field(
        None, max_length=30, description="클립을 캡처한 기기의 모델명", examples=["iPhone 16"]
    )

    @field_validator("metadata")
    @classmethod
    def within_batch_size(cls, value: list[CreateAudioCaptureItemRequest]) -> list[CreateAudioCaptureItemRequest]:
        if len(value) > MAX_BATCH_SIZE:
            raise ValueError(f"한 번에 업로드할 수 있는 클립 수는 {MAX_BATCH_SIZE}개 이하입니다")
        return value

    @field_validator("file")
    @classmethod
    def within_archive_size(cls, value: UploadFile) -> UploadFile:
        if value.size is not None and value.size > convert_size_to_bytes(size=MAX_ARCHIVE_SIZE):
            raise ValueError(f"압축 파일의 최대 크기를 초과했습니다. 최대 크기: {MAX_ARCHIVE_SIZE}")
        return value


class GetAudioCaptureListRequest(PageParams):
    null_fields: ClassVar[set] = {
        "firebase_anon_uid",
        "word_label",
        "label_option_ids",
        "has_memo",
        "date_from",
        "date_to",
    }

    firebase_anon_uid: str | None = Field(
        None,
        max_length=128,
        description="Firebase Authentication 익명 ID",
        examples=["FJTNzziLv9VlWUaOMUUdrWNe3Rm2"],
    )
    word_label: str | None = Field(None, description="연결된 단어명", examples=["안녕"])
    label_option_ids: list[UUID] | None = Field(None, description="클립 라벨 옵션 ID 필터", examples=[[]])
    has_memo: bool | None = Field(None, description="메모가 있는 세그먼트 존재 여부 필터", examples=[True])
    date_from: datetime | None = Field(None, description="캡처 시각 시작 범위", examples=["2026-08-01T00:00:00Z"])
    date_to: datetime | None = Field(None, description="캡처 시각 끝 범위", examples=["2026-08-31T23:59:59Z"])


class AssignAudioCaptureLabelsRequest(BaseRequest):
    label_option_ids: list[UUID] = Field(..., description="지정할 라벨 옵션 ID 목록", examples=[[]])


class MigrateReviewLabelRequest(BaseRequest):
    category: str = Field(..., description="라벨 카테고리 이름", examples=["새 소리"])
    option: str = Field(..., description="라벨 옵션 이름", examples=["안녕"])


class MigrateReviewRequest(BaseRequest):
    empty_str_fields: ClassVar[set] = {"memo"}

    audio_file_id: str = Field(
        ...,
        description="S3 object key",
        examples=["audio_capture/{uid}/{capture_id}/{file_id}/session-xxx.wav"],
    )
    label: list[MigrateReviewLabelRequest] = Field(..., description="라벨 목록", examples=[[]])
    memo: str = Field(..., description="메모 내용", examples=[""])


class MigrateReviewsRequest(BaseRequest):
    reviews: list[MigrateReviewRequest] = Field(..., description="리뷰 목록", examples=[[]])


class ExportAudioSegmentsRequest(BaseRequest):
    null_fields: ClassVar[set] = {"audio_capture_label_option_ids"}

    audio_capture_label_option_ids: list[UUID] | None = Field(
        None,
        description="클립 라벨 옵션 ID 필터",
        examples=[[]],
    )

from datetime import date, datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import Field

from app.legacy.audio_capture.application.dto.audio_segment import GetAudioSegmentDTO
from app.legacy.audio_capture.domain.enums import PhaseEnum
from core.common import CustomBaseModel


class GetAudioCaptureDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word_id", "duration_ms"}

    id: UUID = Field(..., description="캡처 ID")
    firebase_anon_uid: str = Field(..., max_length=128, description="Firebase Authentication 익명 ID")
    client_word_id: str = Field(..., description="클라이언트 단어 ID")
    word_id: UUID | None = Field(None, description="연결된 단어 ID")
    cycle: int = Field(..., description="세션 사이클 번호")
    phase: PhaseEnum = Field(..., description="캡처 세션 구간")
    captured_at: datetime = Field(..., description="클라이언트 캡처 시각")
    duration_ms: int | None = Field(None, description="캡처 길이 ms")
    created_at: datetime = Field(..., description="서버 저장 시각")


class GetAudioCaptureListItemDTO(GetAudioCaptureDTO):
    segment_count: int = Field(..., description="전체 세그먼트 수")
    labeled_count: int = Field(..., description="라벨링된 세그먼트 수")
    has_memo: bool = Field(..., description="메모가 있는 세그먼트 존재 여부")
    label_option_ids: list[UUID] = Field(..., description="클립 라벨 옵션 ID 목록")


class GetAudioCaptureDetailDTO(GetAudioCaptureDTO):
    allow_null_fields: ClassVar[set] = GetAudioCaptureDTO.allow_null_fields | {
        "parrot_species",
        "parrot_birthdate",
        "device_platform",
        "device_os_version",
        "device_model",
        "memo",
    }

    parrot_species: str | None = Field(None, description="앵무새 종")
    parrot_birthdate: date | None = Field(None, description="앵무새 생년월일")
    device_platform: str | None = Field(None, description="클립을 캡처한 기기의 OS")
    device_os_version: str | None = Field(None, description="클립을 캡처한 기기의 OS 버전")
    device_model: str | None = Field(None, description="클립을 캡처한 기기의 모델명")
    memo: str | None = Field(None, description="메모")
    audio_url: str = Field(..., description="원본 오디오 URL")
    segments: list[GetAudioSegmentDTO] = Field(..., description="세그먼트 목록")
    label_option_ids: list[UUID] = Field(..., description="클립 라벨 옵션 ID 목록")


class UpdateAudioCaptureMemoDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"memo"}

    memo: str | None = Field(..., description="메모")


class AssignAudioCaptureLabelsDTO(CustomBaseModel):
    label_option_ids: list[UUID] = Field(..., description="지정할 라벨 옵션 ID 목록")


class MigrateReviewLabelDTO(CustomBaseModel):
    category: str = Field(..., description="라벨 카테고리 이름")
    option: str = Field(..., description="라벨 옵션 이름")


class MigrateReviewDTO(CustomBaseModel):
    audio_file_id: str = Field(..., description="S3 object key")
    label: list[MigrateReviewLabelDTO] = Field(..., description="라벨 목록")
    memo: str = Field(..., description="메모 내용")


class MigrateReviewsDTO(CustomBaseModel):
    reviews: list[MigrateReviewDTO] = Field(..., description="리뷰 목록")


class MigrateReviewResultDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"code", "error_code", "message"}

    status: Literal["success", "rejected"] = Field(..., description="항목의 마이그레이션 결과")
    code: int | None = Field(None, description="거부된 항목의 HTTP 상태 코드")
    error_code: str | None = Field(None, description="거부된 항목의 에러 코드")
    message: str | None = Field(None, description="거부된 항목의 에러 메시지")

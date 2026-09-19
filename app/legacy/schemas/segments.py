from typing import ClassVar
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseRequest, CustomBaseModel


class CreateAudioSegmentRequest(BaseRequest):
    start_ms: int = Field(..., ge=0, description="원본 파일 기준 시작 위치 ms", examples=[0])
    end_ms: int = Field(..., ge=0, description="원본 파일 기준 끝 위치 ms", examples=[1000])


class TrimAudioSegmentRequest(CreateAudioSegmentRequest):
    pass


class AssignAudioSegmentLabelRequest(BaseRequest):
    label_option_id: UUID = Field(
        ...,
        description="지정할 라벨 옵션 ID",
        examples=["0198f4b0-68c0-7000-8000-000000000001"],
    )


class UpdateAudioSegmentMemoRequest(BaseRequest):
    null_fields: ClassVar[set] = {"memo"}

    memo: str | None = Field(..., description="메모. null이면 메모를 지운다", examples=["소리가 선명함"])


class GetAudioSegmentDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"label_option_id", "memo"}

    id: UUID = Field(..., description="세그먼트 ID")
    start_ms: int = Field(..., description="원본 파일 기준 시작 위치 ms")
    end_ms: int = Field(..., description="원본 파일 기준 끝 위치 ms")
    label_option_id: UUID | None = Field(None, description="지정된 라벨 옵션 ID")
    memo: str | None = Field(None, description="메모")
    audio_url: str = Field(..., description="세그먼트 오디오 URL")


class ExportAudioSegmentsRequest(BaseRequest):
    null_fields: ClassVar[set] = {"audio_capture_label_option_ids"}

    audio_capture_label_option_ids: list[UUID] | None = Field(
        None,
        description="클립 라벨 옵션 ID 필터",
        examples=[[]],
    )

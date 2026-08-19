from typing import ClassVar
from uuid import UUID

from pydantic import Field

from core.common import CustomBaseModel


class GetAudioSegmentDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"label_option_id"}

    id: UUID = Field(..., description="세그먼트 ID")
    start_ms: int = Field(..., description="원본 파일 기준 시작 위치 ms")
    end_ms: int = Field(..., description="원본 파일 기준 끝 위치 ms")
    label_option_id: UUID | None = Field(None, description="지정된 라벨 옵션 ID")
    audio_url: str = Field(..., description="세그먼트 오디오 URL")


class CreateAudioSegmentDTO(CustomBaseModel):
    start_ms: int = Field(..., ge=0, description="원본 파일 기준 시작 위치 ms")
    end_ms: int = Field(..., ge=0, description="원본 파일 기준 끝 위치 ms")


class TrimAudioSegmentDTO(CustomBaseModel):
    start_ms: int = Field(..., ge=0, description="원본 파일 기준 시작 위치 ms")
    end_ms: int = Field(..., ge=0, description="원본 파일 기준 끝 위치 ms")


class AssignAudioSegmentLabelDTO(CustomBaseModel):
    label_option_id: UUID = Field(..., description="지정할 라벨 옵션 ID")

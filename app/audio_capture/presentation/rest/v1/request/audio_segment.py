from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateAudioSegmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_ms: int = Field(..., ge=0, description="원본 파일 기준 시작 위치 ms")
    end_ms: int = Field(..., ge=0, description="원본 파일 기준 끝 위치 ms")


class TrimAudioSegmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_ms: int = Field(..., ge=0, description="원본 파일 기준 시작 위치 ms")
    end_ms: int = Field(..., ge=0, description="원본 파일 기준 끝 위치 ms")


class AssignAudioSegmentLabelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label_option_id: UUID = Field(..., description="지정할 라벨 옵션 ID")

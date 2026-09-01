from typing import ClassVar
from uuid import UUID

from pydantic import Field

from core.common.request import BaseRequest


class CreateAudioSegmentRequest(BaseRequest):
    start_ms: int = Field(..., ge=0, description="원본 파일 기준 시작 위치 ms", examples=[0])
    end_ms: int = Field(..., ge=0, description="원본 파일 기준 끝 위치 ms", examples=[1000])


class TrimAudioSegmentRequest(BaseRequest):
    start_ms: int = Field(..., ge=0, description="원본 파일 기준 시작 위치 ms", examples=[0])
    end_ms: int = Field(..., ge=0, description="원본 파일 기준 끝 위치 ms", examples=[1000])


class AssignAudioSegmentLabelRequest(BaseRequest):
    label_option_id: UUID = Field(
        ...,
        description="지정할 라벨 옵션 ID",
        examples=["0198f4b0-68c0-7000-8000-000000000001"],
    )


class UpdateAudioSegmentMemoRequest(BaseRequest):
    null_fields: ClassVar[set] = {"memo"}

    memo: str | None = Field(..., description="메모. null이면 메모를 지운다", examples=["소리가 선명함"])

from app.audio_capture.application.dto import (
    BatchCreateAudioCaptureResultDTO,
    GetAudioCaptureDetailDTO,
    GetAudioCaptureListItemDTO,
)
from core.common.response import BaseResponse


class BatchCreateAudioCaptureResponse(BaseResponse):
    data: dict[str, BatchCreateAudioCaptureResultDTO]


class GetAudioCaptureListResponse(BaseResponse):
    data: list[GetAudioCaptureListItemDTO]


class GetAudioCaptureDetailResponse(BaseResponse):
    data: GetAudioCaptureDetailDTO

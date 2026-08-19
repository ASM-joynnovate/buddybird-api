from app.audio_capture.application.dto.audio_capture import (
    AudioCaptureUploadResultDTO,
    GetAudioCaptureDetailDTO,
    GetAudioCaptureListItemDTO,
)
from core.common.response import BaseResponse


class BatchCreateAudioCaptureResponse(BaseResponse):
    data: dict[str, AudioCaptureUploadResultDTO]


class GetAudioCaptureListResponse(BaseResponse):
    data: list[GetAudioCaptureListItemDTO]


class GetAudioCaptureDetailResponse(BaseResponse):
    data: GetAudioCaptureDetailDTO

from app.audio_capture.application.dto import (
    BatchCreateAudioCaptureResultDTO,
    GetAudioCaptureDetailDTO,
    GetAudioCaptureListItemDTO,
    MigrateReviewResultDTO,
)
from core.common.response import BaseResponse


class BatchCreateAudioCaptureResponse(BaseResponse):
    data: dict[str, BatchCreateAudioCaptureResultDTO]


class GetAudioCaptureListResponse(BaseResponse):
    data: list[GetAudioCaptureListItemDTO]


class GetAudioCaptureDetailResponse(BaseResponse):
    data: GetAudioCaptureDetailDTO


class MigrateReviewsResponse(BaseResponse):
    data: dict[str, MigrateReviewResultDTO]

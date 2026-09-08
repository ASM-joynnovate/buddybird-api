from app.legacy.audio_capture.application.dto import (
    GetAudioCaptureDetailDTO,
    GetAudioCaptureListItemDTO,
    MigrateReviewResultDTO,
)
from core.common.response import BaseResponse


class GetAudioCaptureListResponse(BaseResponse):
    data: list[GetAudioCaptureListItemDTO]


class GetAudioCaptureDetailResponse(BaseResponse):
    data: GetAudioCaptureDetailDTO


class MigrateReviewsResponse(BaseResponse):
    data: dict[str, MigrateReviewResultDTO]

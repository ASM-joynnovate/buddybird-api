from app.audio_capture.application.dto.audio_capture import AudioCaptureUploadResultDTO
from core.common.response import BaseResponse


class BatchCreateAudioCaptureResponse(BaseResponse):
    data: dict[str, AudioCaptureUploadResultDTO]

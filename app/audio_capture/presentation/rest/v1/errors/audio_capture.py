from core.common.errors import CustomError


class AudioCaptureBatchSizeExceededError(CustomError):
    code = 400
    error_code = "AUDIO_CAPTURE__BATCH_SIZE_EXCEEDED"
    message = "한 번에 업로드할 수 있는 클립 수를 초과했습니다."

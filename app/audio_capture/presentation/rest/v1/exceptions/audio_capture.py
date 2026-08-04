from core.common.exceptions import CustomException


class AudioCaptureBatchSizeExceededException(CustomException):
    code = 400
    error_code = "CAPTURE__BATCH_SIZE_EXCEEDED"
    message = "한 번에 업로드할 수 있는 클립 수를 초과했습니다."

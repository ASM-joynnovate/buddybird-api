from core.common.errors import CustomError


class InvalidAudioSegmentRangeError(CustomError):
    code = 400
    error_code = "AUDIO_SEGMENT__INVALID_RANGE"
    message = "세그먼트 끝 위치는 시작 위치보다 커야 합니다."

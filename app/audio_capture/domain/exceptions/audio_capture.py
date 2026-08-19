from core.common.exceptions import CustomException


class UnsupportedAudioFormatException(CustomException):
    code = 400
    error_code = "AUDIO_CAPTURE__UNSUPPORTED_FORMAT"
    message = "지원하지 않는 오디오 형식입니다."

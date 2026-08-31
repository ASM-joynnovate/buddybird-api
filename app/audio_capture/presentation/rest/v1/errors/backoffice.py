from core.common.errors import CustomError


class BackofficePasswordMissingError(CustomError):
    code = 401
    error_code = "AUDIO_CAPTURE__BACKOFFICE_PASSWORD_MISSING"
    message = "백오피스 비밀번호를 입력해 주세요."


class BackofficePasswordInvalidError(CustomError):
    code = 401
    error_code = "AUDIO_CAPTURE__BACKOFFICE_PASSWORD_INVALID"
    message = "백오피스 비밀번호가 올바르지 않습니다."

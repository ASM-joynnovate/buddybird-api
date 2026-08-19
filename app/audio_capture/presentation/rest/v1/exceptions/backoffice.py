from core.common.exceptions import CustomException


class BackofficePasswordMissingException(CustomException):
    code = 401
    error_code = "BACKOFFICE__PASSWORD_MISSING"
    message = "백오피스 비밀번호를 입력해 주세요."


class BackofficePasswordInvalidException(CustomException):
    code = 401
    error_code = "BACKOFFICE__PASSWORD_INVALID"
    message = "백오피스 비밀번호가 올바르지 않습니다."

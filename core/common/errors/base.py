class CustomError(Exception):
    code = 400
    error_code = "COMMON__BAD_REQUEST"
    message = "잘못된 요청입니다."
    detail = None

    def __init__(self, code: int | None = None, message: str | None = None, *, detail: dict | str | None = None):
        if code:
            self.code = code
        if message:
            self.message = message
        if detail:
            self.detail = detail


class ValueObjectEnumError(CustomError):
    code = 400
    error_code = "COMMON__INVALID_ENUM"
    message = "유효하지 않은 Enum 값입니다."


class ResourceNotFoundError(CustomError):
    code = 404
    error_code = "COMMON__RESOURCE_NOT_FOUND"
    message = "요청한 리소스를 찾을 수 없습니다."

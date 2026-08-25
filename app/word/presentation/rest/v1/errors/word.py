from core.common.errors import CustomError


class ReservedClientWordIdError(CustomError):
    code = 400
    error_code = "WORD__RESERVED_CLIENT_WORD_ID"
    message = "preset으로 시작하는 값은 사용할 수 없습니다."

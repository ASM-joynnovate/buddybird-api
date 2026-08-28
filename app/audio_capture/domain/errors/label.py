from core.common.errors import CustomError


class InvalidLabelCategoryTargetError(CustomError):
    code = 400
    error_code = "LABEL__INVALID_CATEGORY_TARGET"
    message = "이 라벨은 해당 대상에 지정할 수 없습니다."

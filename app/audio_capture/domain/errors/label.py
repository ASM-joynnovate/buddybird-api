from core.common.errors import CustomError


class InvalidLabelCategoryTargetError(CustomError):
    code = 400
    error_code = "LABEL__INVALID_CATEGORY_TARGET"
    message = "이 라벨은 해당 대상에 지정할 수 없습니다."


class DuplicateLabelCategoryError(CustomError):
    code = 409
    error_code = "LABEL__DUPLICATE_CATEGORY"
    message = "동일한 이름과 대상을 가진 라벨 카테고리가 이미 존재합니다."


class DuplicateLabelOptionError(CustomError):
    code = 409
    error_code = "LABEL__DUPLICATE_OPTION"
    message = "동일한 이름의 라벨 옵션이 이미 존재합니다."

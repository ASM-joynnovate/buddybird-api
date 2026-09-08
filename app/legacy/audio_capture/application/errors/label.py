from core.common.errors import CustomError


class DuplicateLabelCategoryError(CustomError):
    code = 409
    error_code = "AUDIO_CAPTURE__DUPLICATE_LABEL_CATEGORY"
    message = "동일한 이름과 대상을 가진 라벨 카테고리가 이미 존재합니다."


class DuplicateLabelOptionError(CustomError):
    code = 409
    error_code = "AUDIO_CAPTURE__DUPLICATE_LABEL_OPTION"
    message = "동일한 이름의 라벨 옵션이 이미 존재합니다."

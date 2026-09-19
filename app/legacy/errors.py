from app.errors import CustomError


class DuplicateLabelCategoryError(CustomError):
    code = 409
    error_code = "AUDIO_CAPTURE__DUPLICATE_LABEL_CATEGORY"
    message = "동일한 이름과 대상을 가진 라벨 카테고리가 이미 존재합니다."


class DuplicateLabelOptionError(CustomError):
    code = 409
    error_code = "AUDIO_CAPTURE__DUPLICATE_LABEL_OPTION"
    message = "동일한 이름의 라벨 옵션이 이미 존재합니다."


class DuplicateReviewAudioFileIdError(CustomError):
    code = 400
    error_code = "AUDIO_CAPTURE__DUPLICATE_REVIEW_AUDIO_FILE_ID"
    message = "중복된 리뷰 오디오 파일 ID가 있습니다."


class InvalidAudioSegmentRangeError(CustomError):
    code = 400
    error_code = "AUDIO_CAPTURE__INVALID_SEGMENT_RANGE"
    message = "세그먼트 끝 위치는 시작 위치보다 커야 합니다."


class InvalidLabelCategoryTargetError(CustomError):
    code = 400
    error_code = "AUDIO_CAPTURE__INVALID_LABEL_CATEGORY_TARGET"
    message = "이 라벨은 해당 대상에 지정할 수 없습니다."


class BackofficePasswordMissingError(CustomError):
    code = 401
    error_code = "AUDIO_CAPTURE__BACKOFFICE_PASSWORD_MISSING"
    message = "백오피스 비밀번호를 입력해 주세요."


class BackofficePasswordInvalidError(CustomError):
    code = 401
    error_code = "AUDIO_CAPTURE__BACKOFFICE_PASSWORD_INVALID"
    message = "백오피스 비밀번호가 올바르지 않습니다."

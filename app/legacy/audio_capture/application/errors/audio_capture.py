from core.common.errors import CustomError


class DuplicateReviewAudioFileIdError(CustomError):
    code = 400
    error_code = "AUDIO_CAPTURE__DUPLICATE_REVIEW_AUDIO_FILE_ID"
    message = "중복된 리뷰 오디오 파일 ID가 있습니다."

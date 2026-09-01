from core.common.errors import CustomError


class AudioCaptureArchiveInvalidError(CustomError):
    code = 400
    error_code = "AUDIO_CAPTURE__ARCHIVE_INVALID"
    message = "압축 파일을 풀 수 없습니다."


class AudioCaptureArchiveEntryNotFoundError(CustomError):
    code = 400
    error_code = "AUDIO_CAPTURE__ARCHIVE_ENTRY_NOT_FOUND"
    message = "압축 파일 안에서 해당 오디오를 찾을 수 없습니다."

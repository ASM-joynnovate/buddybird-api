from core.common.exceptions import CustomException


class AudioCaptureArchiveInvalidException(CustomException):
    code = 400
    error_code = "CAPTURE__ARCHIVE_INVALID"
    message = "압축 파일을 풀 수 없습니다."


class AudioCaptureArchiveEntryNotFoundException(CustomException):
    code = 400
    error_code = "CAPTURE__ARCHIVE_ENTRY_NOT_FOUND"
    message = "압축 파일 안에서 해당 오디오를 찾을 수 없습니다."

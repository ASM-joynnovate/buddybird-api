from core.common.exceptions import CustomException


class DetectFileMimeTypeFailedException(CustomException):
    code = 400
    error_code = "FILE__DETECT_MIME_TYPE_FAILED"
    message = "파일의 타입을 감지할 수 없습니다. 파일이 올바른 형식인지 확인해주세요."


class NotAllowedFileTypeException(CustomException):
    code = 400
    error_code = "FILE__NOT_ALLOWED_FILE_TYPE"
    message = "허용되지 않는 파일 형식입니다. 지원되는 파일 형식을 확인해주세요."


class FileSizeExceededException(CustomException):
    code = 400
    error_code = "FILE__SIZE_EXCEEDED"
    message = "파일 크기가 허용된 최대 크기를 초과했습니다."

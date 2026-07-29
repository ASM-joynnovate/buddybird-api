import magic

from app.shared_kernel.domain.exceptions import DetectFileMimeTypeFailedException
from app.shared_kernel.domain.interfaces.services import IFileAnalyzer


class FileAnalyzer(IFileAnalyzer):
    def get_mime_type(self, *, file: bytes) -> str:
        file_type = magic.from_buffer(file, mime=True)
        if not file_type:
            raise DetectFileMimeTypeFailedException()

        return file_type

    def get_file_size(self, *, file: bytes) -> int:
        return len(file)

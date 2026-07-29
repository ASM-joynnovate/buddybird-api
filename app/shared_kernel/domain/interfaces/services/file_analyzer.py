class IFileAnalyzer:
    def get_mime_type(self, *, file: bytes) -> str:
        pass

    def get_file_size(self, *, file: bytes) -> int:
        pass

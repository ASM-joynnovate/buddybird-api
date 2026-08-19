class IAudioAnalyzer:
    def get_duration_ms(self, *, file: bytes) -> int | None:
        pass

    def trim(self, *, file: bytes, start_ms: int, end_ms: int) -> bytes:
        pass

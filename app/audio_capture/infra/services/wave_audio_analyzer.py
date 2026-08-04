import io
import wave

from app.audio_capture.domain.interfaces.services import IAudioAnalyzer


class WaveAudioAnalyzer(IAudioAnalyzer):
    def get_duration_ms(self, *, file: bytes) -> int | None:
        try:
            with wave.open(io.BytesIO(file), "rb") as audio:
                frames = audio.getnframes()
                rate = audio.getframerate()
        except wave.Error, EOFError:
            return None

        if not rate:
            return None

        return int(frames / rate * 1000)

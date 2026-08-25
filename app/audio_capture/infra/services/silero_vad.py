import io
import wave

import torch
from silero_vad import get_speech_timestamps, load_silero_vad
from torchaudio.functional import resample

from app.audio_capture.domain.errors import UnsupportedAudioFormatError
from app.audio_capture.domain.interfaces.services import IVadService


class SileroVadService(IVadService):
    def __init__(self):
        self._model = load_silero_vad()

    def detect(self, *, file: bytes) -> list[tuple[int, int]]:
        # WAV 헤더와 PCM 프레임 읽기
        with wave.open(io.BytesIO(file), "rb") as wav:
            sample_rate = wav.getframerate()
            n_channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            frames = wav.readframes(wav.getnframes())

        # 16비트 PCM만 허용
        if sample_width != 2:
            raise UnsupportedAudioFormatError

        # 16비트 정수 샘플을 -1 ~ 1 실수로 변환
        samples = torch.frombuffer(bytearray(frames), dtype=torch.int16).float() / 32768.0

        # 스테레오는 mono로 변환
        if n_channels > 1:
            samples = samples.reshape(-1, n_channels).mean(dim=1)

        # 16kHz로 리샘플
        if sample_rate != 16000:
            samples = resample(samples, orig_freq=sample_rate, new_freq=16000)

        # 음성 구간 감지
        timestamps = get_speech_timestamps(
            samples, self._model, sampling_rate=16000, return_seconds=True, threshold=0.1
        )

        # ms로 변환
        return [(int(timestamp["start"] * 1000), int(timestamp["end"] * 1000)) for timestamp in timestamps]

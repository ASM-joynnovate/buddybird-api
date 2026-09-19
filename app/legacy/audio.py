import io
import wave


def trim(*, file: bytes, start_ms: int, end_ms: int) -> bytes:
    with wave.open(io.BytesIO(file), "rb") as src:
        n_channels = src.getnchannels()
        sampwidth = src.getsampwidth()
        rate = src.getframerate()
        total_frames = src.getnframes()

        start_frame = min(total_frames, max(0, int(start_ms / 1000 * rate)))
        end_frame = min(total_frames, int(end_ms / 1000 * rate))

        src.setpos(start_frame)

        frames = src.readframes(max(0, end_frame - start_frame))

    out = io.BytesIO()

    with wave.open(out, "wb") as dst:
        dst.setnchannels(n_channels)
        dst.setsampwidth(sampwidth)
        dst.setframerate(rate)
        dst.writeframes(frames)

    return out.getvalue()

from .audio_capture import init_audio_capture_mappers
from .audio_segment import init_audio_segment_mappers
from .label import init_label_mappers
from .shared_kernel import init_shared_kernel_mappers
from .word import init_word_mappers


def init_orm_mappers() -> None:
    init_shared_kernel_mappers()
    init_word_mappers()
    init_label_mappers()
    init_audio_capture_mappers()
    init_audio_segment_mappers()


__all__ = ["init_orm_mappers"]

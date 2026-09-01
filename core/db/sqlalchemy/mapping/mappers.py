from core.db.sqlalchemy.mapping.audio_capture import init_audio_capture_mappers
from core.db.sqlalchemy.mapping.audio_segment import init_audio_segment_mappers
from core.db.sqlalchemy.mapping.file import init_file_mappers
from core.db.sqlalchemy.mapping.label import init_label_mappers
from core.db.sqlalchemy.mapping.word import init_word_mappers


def init_orm_mappers() -> None:
    init_file_mappers()
    init_word_mappers()
    init_label_mappers()
    init_audio_capture_mappers()
    init_audio_segment_mappers()

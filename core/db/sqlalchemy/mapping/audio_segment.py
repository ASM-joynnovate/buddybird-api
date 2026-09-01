from sqlalchemy.orm import composite, relationship

from core.db.sqlalchemy.mapping.base import mapper_registry
from core.db.sqlalchemy.models import audio_segment_table


def init_audio_segment_mappers() -> None:
    from app.audio_capture.domain.entities.audio_segment import AudioSegment
    from app.audio_capture.domain.value_objects import AudioSegmentRange
    from app.shared_kernel.domain.entities.file import File

    mapper_registry.map_imperatively(
        AudioSegment,
        audio_segment_table,
        version_id_col=audio_segment_table.c.version_id,
        properties={
            "range": composite(
                AudioSegmentRange,
                audio_segment_table.c.start_ms,
                audio_segment_table.c.end_ms,
            ),
            "audio_file": relationship(
                File,
                primaryjoin=audio_segment_table.c.audio_file_id == File.id,
                lazy="selectin",
            ),
        },
    )

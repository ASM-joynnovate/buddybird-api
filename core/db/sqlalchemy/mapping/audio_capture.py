from sqlalchemy.orm import relationship

from core.db.sqlalchemy.mapping.base import mapper_registry
from core.db.sqlalchemy.models import audio_capture_label_table, audio_capture_table


def init_audio_capture_mappers() -> None:
    from app.audio_capture.domain.entities.audio_capture import AudioCapture
    from app.audio_capture.domain.entities.label import LabelOption
    from app.shared_kernel.domain.entities.file import File

    mapper_registry.map_imperatively(
        AudioCapture,
        audio_capture_table,
        version_id_col=audio_capture_table.c.version_id,
        properties={
            "audio_file": relationship(
                File,
                primaryjoin=audio_capture_table.c.audio_file_id == File.id,
                lazy="selectin",
            ),
            "label_options": relationship(
                LabelOption,
                secondary=audio_capture_label_table,
                lazy="selectin",
            ),
        },
    )

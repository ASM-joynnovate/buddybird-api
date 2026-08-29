from sqlalchemy.orm import relationship

from core.db.sqlalchemy.mapping.base import mapper_registry
from core.db.sqlalchemy.models import audio_capture_label_table, audio_capture_table


def init_audio_capture_mappers():
    from app.audio_capture.domain.entities.audio_capture import AudioCapture as AudioCaptureEntity
    from app.audio_capture.domain.entities.label import LabelOption as LabelOptionEntity
    from app.shared_kernel.domain.entities.file import File as FileEntity

    mapper_registry.map_imperatively(
        AudioCaptureEntity,
        audio_capture_table,
        version_id_col=audio_capture_table.c.version_id,
        properties={
            "audio_file": relationship(
                FileEntity,
                primaryjoin=audio_capture_table.c.audio_file_id == FileEntity.id,
                uselist=False,
                lazy="selectin",
            ),
            "label_options": relationship(
                LabelOptionEntity,
                secondary=audio_capture_label_table,
                lazy="selectin",
            ),
        },
    )

from sqlalchemy.orm import relationship

from core.db.sqlalchemy.mapping.base import mapper_registry
from core.db.sqlalchemy.models import word_table


def init_word_mappers() -> None:
    from app.shared_kernel.domain.entities.file import File
    from app.word.domain.entities.word import Word

    mapper_registry.map_imperatively(
        Word,
        word_table,
        version_id_col=word_table.c.version_id,
        properties={
            "audio_file": relationship(
                File,
                primaryjoin=word_table.c.audio_file_id == File.id,
                lazy="selectin",
            )
        },
    )

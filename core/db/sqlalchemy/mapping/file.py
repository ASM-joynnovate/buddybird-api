from core.db.sqlalchemy.mapping.base import mapper_registry
from core.db.sqlalchemy.models import file_table


def init_file_mappers() -> None:
    from app.shared_kernel.domain.entities.file import File

    mapper_registry.map_imperatively(
        File,
        file_table,
        version_id_col=file_table.c.version_id,
    )

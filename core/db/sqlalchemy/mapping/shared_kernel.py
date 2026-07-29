from core.db.sqlalchemy.mapping.base import mapper_registry
from core.db.sqlalchemy.models import file_table


def init_shared_kernel_mappers():
    from app.shared_kernel.domain.entities.file import File as FileEntity
    mapper_registry.map_imperatively(
        FileEntity,
        file_table,
        version_id_col=file_table.c.version_id,
    )
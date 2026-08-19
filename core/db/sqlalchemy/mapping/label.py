from sqlalchemy import and_
from sqlalchemy.orm import relationship

from core.db.sqlalchemy.mapping.base import mapper_registry
from core.db.sqlalchemy.models import label_category_table, label_option_table


def init_label_mappers():
    from app.audio_capture.domain.entities.label import LabelCategory, LabelOption

    mapper_registry.map_imperatively(
        LabelOption,
        label_option_table,
        version_id_col=label_option_table.c.version_id,
    )
    mapper_registry.map_imperatively(
        LabelCategory,
        label_category_table,
        version_id_col=label_category_table.c.version_id,
        properties={
            "options": relationship(
                LabelOption,
                primaryjoin=and_(
                    label_category_table.c.id == LabelOption.category_id,
                    label_option_table.c.is_deleted.is_(False),
                ),
                viewonly=True,
                uselist=True,
                lazy="selectin",
                order_by=label_option_table.c.display_order,
            ),
        },
    )

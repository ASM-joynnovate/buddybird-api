from sqlalchemy import UUID, Boolean, Column, ForeignKey, Integer, String, Text

from app.audio_capture.domain.enum import LabelCategoryTargetEnum
from core.db.sqlalchemy.models.base import BaseTable, metadata

label_category_table = BaseTable(
    "label_categories",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("name", String(100), nullable=False),
    Column("display_order", Integer, nullable=False, default=0),
    Column("target", Text, nullable=False, server_default=LabelCategoryTargetEnum.SEGMENT.value),
    Column("is_deleted", Boolean, nullable=False, default=False),
)

label_option_table = BaseTable(
    "label_options",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("category_id", UUID, ForeignKey("label_categories.id"), nullable=False),
    Column("name", String(100), nullable=False),
    Column("display_order", Integer, nullable=False, default=0),
    Column("is_deleted", Boolean, nullable=False, default=False),
)

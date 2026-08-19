from sqlalchemy import UUID, Boolean, Column, ForeignKey, Integer, String, UniqueConstraint

from core.db.sqlalchemy.models.base import BaseTable, metadata

label_category_table = BaseTable(
    "label_categories",
    metadata,
    Column("id", UUID, primary_key=True),
    Column("name", String(100), nullable=False, unique=True),
    Column("display_order", Integer, nullable=False, default=0),
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
    UniqueConstraint("category_id", "name"),
)

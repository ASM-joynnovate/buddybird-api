from sqlalchemy import UUID, BigInteger, Boolean, Column, String
from uuid_utils import uuid7

from core.db.sqlalchemy.models.base import BaseTable, metadata

file_table = BaseTable(
    "files",
    metadata,
    Column("id", UUID, primary_key=True, default=lambda: str(uuid7())),
    Column("file_name", String(255), index=True, nullable=False),
    Column("file_path", String(255), nullable=False),
    Column("file_size", BigInteger, nullable=False),
    Column("file_type", String(50), nullable=False),
    Column("is_deleted", Boolean, nullable=False, default=False),
)

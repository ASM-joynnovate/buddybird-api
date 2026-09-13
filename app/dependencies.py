import secrets
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.db import session_factory
from app.errors import BackofficePasswordInvalidError, BackofficePasswordMissingError
from app.s3 import S3StorageClient, get_s3


async def get_db() -> AsyncIterator[AsyncSession]:
    async with session_factory() as db:
        yield db


def verify_backoffice_password(x_backoffice_password: Annotated[str | None, Header()] = None) -> None:
    if x_backoffice_password is None:
        raise BackofficePasswordMissingError

    if not secrets.compare_digest(x_backoffice_password, config.BACKOFFICE_PASSWORD):
        raise BackofficePasswordInvalidError


DBSession = Annotated[AsyncSession, Depends(get_db)]
Storage = Annotated[S3StorageClient, Depends(get_s3)]

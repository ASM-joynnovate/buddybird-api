import secrets
from typing import Annotated

from fastapi import Header

from app.audio_capture.presentation.rest.v1.errors import (
    BackofficePasswordInvalidError,
    BackofficePasswordMissingError,
)
from core.config import config


async def verify_backoffice_password(x_backoffice_password: Annotated[str | None, Header()] = None) -> None:
    if x_backoffice_password is None:
        raise BackofficePasswordMissingError
    if not secrets.compare_digest(x_backoffice_password, config.BACKOFFICE_PASSWORD):
        raise BackofficePasswordInvalidError

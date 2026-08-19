import secrets

from fastapi import Header

from app.audio_capture.presentation.rest.v1.exceptions.backoffice import (
    BackofficePasswordInvalidException,
    BackofficePasswordMissingException,
)
from core.config import config


async def verify_backoffice_password(x_backoffice_password: str | None = Header(None)) -> None:
    if x_backoffice_password is None:
        raise BackofficePasswordMissingException
    if not secrets.compare_digest(x_backoffice_password, config.BACKOFFICE_PASSWORD):
        raise BackofficePasswordInvalidException

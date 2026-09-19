import secrets
from typing import Annotated

from fastapi import Header

from app.config import config
from app.legacy.errors import BackofficePasswordInvalidError, BackofficePasswordMissingError


def verify_backoffice_password(x_backoffice_password: Annotated[str | None, Header()] = None) -> None:
    if x_backoffice_password is None:
        raise BackofficePasswordMissingError

    if not secrets.compare_digest(x_backoffice_password, config.BACKOFFICE_PASSWORD):
        raise BackofficePasswordInvalidError

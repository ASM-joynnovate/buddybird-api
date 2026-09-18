from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.db import get_or_404, session_factory
from app.errors import AuthenticationError, DeviceNotRegisteredError, ResourceNotFoundError
from app.middlewares import AuthContext
from app.models import Device, Parrot, User, Word
from app.s3 import S3StorageClient, get_s3


async def get_db() -> AsyncIterator[AsyncSession]:
    async with session_factory() as db:
        yield db


DBSession = Annotated[AsyncSession, Depends(get_db)]
Storage = Annotated[S3StorageClient, Depends(get_s3)]

bearer = HTTPBearer(auto_error=False, scheme_name="Bearer", bearerFormat="JWT")


async def require_auth_context(
    request: Request,
    x_buddybird_client: Annotated[str | None, Header(alias="X-BuddyBird-Client")] = None,
    _credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer)] = None,
) -> AuthContext:
    if x_buddybird_client != "mobile":
        raise AuthenticationError

    origin = request.headers.get("Origin")

    if origin is not None and origin not in config.FRONTEND_CORS_ORIGIN:
        raise AuthenticationError

    if (error := getattr(request.state, "auth_error", None)) is not None:
        raise error

    if not isinstance(request.user, AuthContext):
        raise AuthenticationError

    return request.user


Authenticated = Annotated[AuthContext, Depends(require_auth_context)]


async def require_active_user(context: Authenticated, db: DBSession) -> User:
    user = await db.scalar(select(User).where(User.auth_user_id == context.auth_user_id))

    if user is None:
        raise AuthenticationError

    return user


ActiveUser = Annotated[User, Depends(require_active_user)]


async def require_device(
    user: ActiveUser,
    db: DBSession,
    x_device_id: Annotated[UUID | None, Header(alias="X-Device-Id")] = None,
) -> Device:
    if x_device_id is None:
        raise DeviceNotRegisteredError

    device = await db.scalar(select(Device).where(Device.user_id == user.id, Device.client_device_id == x_device_id))

    if device is None:
        raise DeviceNotRegisteredError

    return device


ActiveDevice = Annotated[Device, Depends(require_device)]


async def require_parrot(user: ActiveUser, db: DBSession, parrot_id: UUID) -> Parrot:
    parrot = await get_or_404(db=db, model=Parrot, id=parrot_id)

    if parrot.user_id != user.id:
        raise ResourceNotFoundError

    return parrot


async def require_word(user: ActiveUser, db: DBSession, word_id: UUID) -> Word:
    word = await get_or_404(db=db, model=Word, id=word_id)

    if word.user_id != user.id:
        raise ResourceNotFoundError

    return word

import re
import secrets
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

import sentry_sdk
from fastapi import Depends, Header, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.db import get_or_404, session_factory
from app.enums import LocaleEnum
from app.errors import (
    AuthenticationError,
    BackofficePasswordInvalidError,
    BackofficePasswordMissingError,
    BackofficeReadonlyError,
    DeviceNotRegisteredError,
    ResourceNotFoundError,
)
from app.middlewares import AuthContext
from app.models import (
    AbuseReport,
    Ad,
    Announcement,
    AppUpdate,
    Consent,
    Device,
    FeedItem,
    Notification,
    NotificationSettingGroup,
    NotificationSettingItem,
    Parrot,
    PresetWord,
    Session,
    SessionEvent,
    SessionSound,
    User,
    Word,
)
from app.r2 import R2StorageClient, get_r2


async def get_db() -> AsyncIterator[AsyncSession]:
    async with session_factory() as db:
        yield db


DBSession = Annotated[AsyncSession, Depends(get_db)]
Storage = Annotated[R2StorageClient, Depends(get_r2)]

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

    sentry_sdk.set_user({"id": str(user.id)})
    sentry_sdk.set_attribute("user.id", str(user.id))

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


async def require_user_device(user: ActiveUser, db: DBSession, device_id: UUID) -> Device:
    device = await get_or_404(db=db, model=Device, id=device_id)

    if device.user_id != user.id:
        raise ResourceNotFoundError

    return device


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


async def require_session(user: ActiveUser, db: DBSession, session_id: UUID) -> Session:
    session = await get_or_404(db=db, model=Session, id=session_id)

    if session.user_id != user.id:
        raise ResourceNotFoundError

    return session


async def require_session_sound(
    session: Annotated[Session, Depends(require_session)], db: DBSession, session_sound_id: UUID
) -> SessionSound:
    sound = await get_or_404(db=db, model=SessionSound, id=session_sound_id)

    if sound.session_id != session.id:
        raise ResourceNotFoundError

    return sound


async def require_session_event(
    session: Annotated[Session, Depends(require_session)], db: DBSession, session_event_id: UUID
) -> SessionEvent:
    event = await get_or_404(db=db, model=SessionEvent, id=session_event_id)

    if event.session_id != session.id:
        raise ResourceNotFoundError

    return event


async def require_notification(user: ActiveUser, db: DBSession, notification_id: UUID) -> Notification:
    notification = await get_or_404(db=db, model=Notification, id=notification_id)

    if notification.user_id != user.id:
        raise ResourceNotFoundError

    return notification


async def require_announcement(db: DBSession, announcement_id: UUID) -> Announcement:
    return await get_or_404(db=db, model=Announcement, id=announcement_id)


async def require_ad(db: DBSession, ad_id: UUID) -> Ad:
    return await get_or_404(db=db, model=Ad, id=ad_id)


async def require_preset_word(db: DBSession, preset_word_id: UUID) -> PresetWord:
    return await get_or_404(db=db, model=PresetWord, id=preset_word_id)


async def require_backoffice(
    request: Request,
    x_backoffice_password: Annotated[str | None, Header(alias="X-Backoffice-Password")] = None,
) -> None:
    if x_backoffice_password is None:
        raise BackofficePasswordMissingError

    if secrets.compare_digest(x_backoffice_password.encode(), config.BACKOFFICE_PASSWORD.encode()):
        return

    readonly_password = config.BACKOFFICE_READONLY_PASSWORD
    readonly_authorized = readonly_password is not None and secrets.compare_digest(
        x_backoffice_password.encode(),
        readonly_password.encode(),
    )

    if not readonly_authorized:
        raise BackofficePasswordInvalidError

    if request.method != "GET":
        raise BackofficeReadonlyError


async def require_backoffice_user(db: DBSession, user_id: UUID) -> User:
    stmt = select(User).where(User.id == user_id).execution_options(include_deleted=True)
    user = await db.scalar(stmt)

    if user is None:
        raise ResourceNotFoundError

    return user


async def require_backoffice_parrot(
    user: Annotated[User, Depends(require_backoffice_user)], db: DBSession, parrot_id: UUID
) -> Parrot:
    parrot = await get_or_404(db=db, model=Parrot, id=parrot_id)

    if parrot.user_id != user.id:
        raise ResourceNotFoundError

    return parrot


async def require_backoffice_session(db: DBSession, session_id: UUID) -> Session:
    return await get_or_404(db=db, model=Session, id=session_id)


async def require_backoffice_session_sound(
    session: Annotated[Session, Depends(require_backoffice_session)], db: DBSession, session_sound_id: UUID
) -> SessionSound:
    sound = await get_or_404(db=db, model=SessionSound, id=session_sound_id)

    if sound.session_id != session.id:
        raise ResourceNotFoundError

    return sound


async def require_backoffice_session_event(
    session: Annotated[Session, Depends(require_backoffice_session)], db: DBSession, session_event_id: UUID
) -> SessionEvent:
    event = await get_or_404(db=db, model=SessionEvent, id=session_event_id)

    if event.session_id != session.id:
        raise ResourceNotFoundError

    return event


async def require_consent(db: DBSession, consent_id: UUID) -> Consent:
    return await get_or_404(db=db, model=Consent, id=consent_id)


async def require_app_update(db: DBSession, app_update_id: UUID) -> AppUpdate:
    return await get_or_404(db=db, model=AppUpdate, id=app_update_id)


async def require_notification_setting_group(db: DBSession, group_id: UUID) -> NotificationSettingGroup:
    return await get_or_404(db=db, model=NotificationSettingGroup, id=group_id)


async def require_notification_setting_item(db: DBSession, item_id: UUID) -> NotificationSettingItem:
    return await get_or_404(db=db, model=NotificationSettingItem, id=item_id)


async def require_feed_item(db: DBSession, feed_item_id: UUID) -> FeedItem:
    return await get_or_404(db=db, model=FeedItem, id=feed_item_id)


async def require_abuse_report(db: DBSession, abuse_report_id: UUID) -> AbuseReport:
    return await get_or_404(db=db, model=AbuseReport, id=abuse_report_id)


async def get_locale(accept_language: Annotated[str | None, Header(alias="Accept-Language")] = None) -> LocaleEnum:
    return LocaleEnum.ranked(accept_language)[0]


Locale = Annotated[LocaleEnum, Depends(get_locale)]


async def get_country(
    cf_ipcountry: Annotated[str | None, Header(alias="CF-IPCountry")] = None,
) -> str | None:
    if cf_ipcountry is not None and re.fullmatch("[A-Z]{2}", cf_ipcountry):
        return cf_ipcountry

    return None


Country = Annotated[str | None, Depends(get_country)]

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import SessionActorEnum, SessionEventKindEnum, SessionStatusEnum
from app.errors import DeviceSaveUnavailableError
from app.models import Device, Session, SessionEvent, User
from app.schemas.devices import (
    DeviceClientDTO,
    DeviceDTO,
    RegisterDeviceRequest,
    UpdateDeviceRequest,
    UpdatePushTokenRequest,
)


def build_device_dto(device: Device) -> DeviceDTO:
    return DeviceDTO(
        id=device.id,
        client_device_id=device.client_device_id,
        timezone=device.timezone,
        locale=device.locale,
        last_seen_at=device.last_seen_at,
        client=DeviceClientDTO(
            platform=device.platform,
            os_version=device.os_version,
            model=device.model,
            app_version=device.app_version,
        ),
        push_registered=device.push_token is not None,
    )


async def finish_running_sessions(*, db: AsyncSession, device: Device, now: datetime) -> list[UUID]:
    sessions = (
        await db.scalars(
            select(Session).where(
                Session.station_device_id == device.id, Session.status == SessionStatusEnum.RUNNING.value
            )
        )
    ).all()

    for session in sessions:
        session.status = SessionStatusEnum.FINISHED.value
        session.ended_at = now
        session.ended_by = SessionActorEnum.SERVER.value

        db.add(
            SessionEvent(
                session_id=session.id,
                kind=SessionEventKindEnum.SESSION_FINISHED.value,
                occurred_at=now,
            )
        )

    return [session.id for session in sessions]


async def get_list(*, db: AsyncSession, user: User) -> list[DeviceDTO]:
    devices = (await db.scalars(select(Device).where(Device.user_id == user.id).order_by(Device.created_at))).all()

    return [build_device_dto(device) for device in devices]


@transactional(unavailable_error=DeviceSaveUnavailableError)
async def register(*, db: AsyncSession, user: User, data: RegisterDeviceRequest) -> DeviceDTO:
    now = datetime.now(UTC)
    device = await db.scalar(
        select(Device)
        .where(Device.user_id == user.id, Device.client_device_id == data.client_device_id)
        .execution_options(include_deleted=True)
    )

    if device is None:
        device = Device(
            user_id=user.id,
            client_device_id=data.client_device_id,
            platform=data.platform,
            os_version=data.os_version,
            model=data.model,
            app_version=data.app_version,
            timezone=data.timezone,
            locale=data.locale.value,
            last_seen_at=now,
            is_deleted=False,
        )
        db.add(device)
    else:
        device.platform = data.platform
        device.os_version = data.os_version
        device.model = data.model
        device.app_version = data.app_version
        device.timezone = data.timezone
        device.locale = data.locale.value
        device.last_seen_at = now
        device.is_deleted = False

    await db.flush()

    return build_device_dto(device)


@transactional(unavailable_error=DeviceSaveUnavailableError)
async def update_push_token(*, db: AsyncSession, device: Device, data: UpdatePushTokenRequest) -> DeviceDTO:
    device.push_token = data.token

    await db.flush()

    return build_device_dto(device)


@transactional(unavailable_error=DeviceSaveUnavailableError)
async def update_me(*, db: AsyncSession, device: Device, data: UpdateDeviceRequest) -> DeviceDTO:
    for name, value in data.model_dump(exclude_unset=True).items():
        setattr(device, name, value)

    await db.flush()

    return build_device_dto(device)


@transactional(unavailable_error=DeviceSaveUnavailableError)
async def delete(*, db: AsyncSession, device: Device) -> list[UUID]:
    device.is_deleted = True
    device.push_token = None

    session_ids = await finish_running_sessions(db=db, device=device, now=datetime.now(UTC))

    await db.flush()

    return session_ids

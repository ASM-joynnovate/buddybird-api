from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import DeviceRoleEnum, SessionActorEnum, SessionEventKindEnum, SessionStatusEnum
from app.errors import DeviceSaveUnavailableError
from app.models import Device, Session, SessionEvent, User
from app.schemas.devices import (
    DeviceClientDTO,
    DeviceDTO,
    DevicePushDTO,
    RegisterDeviceRequest,
    UpdateDeviceRequest,
    UpdatePushTokenRequest,
)


def build_device_dto(device: Device) -> DeviceDTO:
    push = None

    if device.push_token is not None:
        push = DevicePushDTO(token=device.push_token)

    return DeviceDTO(
        id=device.id,
        client_device_id=device.client_device_id,
        role=device.role,
        timezone=device.timezone,
        last_seen_at=device.last_seen_at,
        client=DeviceClientDTO(
            platform=device.platform,
            os_version=device.os_version,
            model=device.model,
            app_version=device.app_version,
        ),
        push=push,
    )


async def finish_running_sessions(*, db: AsyncSession, device: Device, now: datetime) -> None:
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
                occurred_by=SessionActorEnum.SERVER.value,
            )
        )


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
    others = (
        await db.scalars(
            select(Device).where(
                Device.user_id == user.id,
                Device.role == data.role.value,
                Device.client_device_id != data.client_device_id,
            )
        )
    ).all()

    for other in others:
        other.is_deleted = True

        await finish_running_sessions(db=db, device=other, now=now)

    await db.flush()

    if device is None:
        device = Device(
            user_id=user.id,
            client_device_id=data.client_device_id,
            role=data.role.value,
            platform=data.platform,
            os_version=data.os_version,
            model=data.model,
            app_version=data.app_version,
            timezone=data.timezone,
            last_seen_at=now,
            is_deleted=False,
        )
        db.add(device)
    else:
        if device.role == DeviceRoleEnum.STATION.value and data.role != DeviceRoleEnum.STATION:
            await finish_running_sessions(db=db, device=device, now=now)

        device.role = data.role.value
        device.platform = data.platform
        device.os_version = data.os_version
        device.model = data.model
        device.app_version = data.app_version
        device.timezone = data.timezone
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
    changes = data.model_dump(exclude_unset=True)

    if "app_version" in changes:
        device.app_version = changes["app_version"]

    if "os_version" in changes:
        device.os_version = changes["os_version"]

    if "timezone" in changes:
        device.timezone = changes["timezone"]

    await db.flush()

    return build_device_dto(device)


@transactional(unavailable_error=DeviceSaveUnavailableError)
async def delete_me(*, db: AsyncSession, device: Device) -> None:
    device.is_deleted = True

    if device.role == DeviceRoleEnum.STATION.value:
        await finish_running_sessions(db=db, device=device, now=datetime.now(UTC))

    await db.flush()

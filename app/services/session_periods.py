from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device, Session


async def get_active_periods(
    *, db: AsyncSession, sessions: Sequence[Session]
) -> dict[UUID, list[tuple[datetime, datetime]]]:
    stmt = (
        select(Device.id, Device.timezone)
        .where(Device.id.in_({session.station_device_id for session in sessions}))
        .execution_options(include_deleted=True)
    )
    timezones = dict((await db.execute(stmt)).all())
    now = datetime.now(UTC)
    active_periods = {}

    for session in sessions:
        ended_at = session.ended_at or now

        if session.sleep_at is None or session.sleep_at == session.wake_at:
            active_periods[session.id] = [(session.started_at, ended_at)]
            continue

        try:
            zone = ZoneInfo(timezones[session.station_device_id] or "UTC")
        except ZoneInfoNotFoundError, ValueError:
            zone = ZoneInfo("UTC")

        periods = []
        active_from = session.started_at
        day = session.started_at.astimezone(zone).date() - timedelta(days=1)

        while active_from < ended_at:
            sleep_from = datetime.combine(day, session.sleep_at, tzinfo=zone)
            wake_day = day if session.wake_at > session.sleep_at else day + timedelta(days=1)
            sleep_until = datetime.combine(wake_day, session.wake_at, tzinfo=zone)

            if sleep_until > active_from:
                if sleep_from > active_from:
                    periods.append((active_from, min(sleep_from, ended_at)))

                active_from = max(active_from, sleep_until)

            day += timedelta(days=1)

        active_periods[session.id] = periods

    return active_periods


async def get_active_durations(*, db: AsyncSession, sessions: Sequence[Session]) -> dict[UUID, int]:
    active_periods = await get_active_periods(db=db, sessions=sessions)

    return {
        session_id: sum((ended_at - started_at for started_at, ended_at in periods), timedelta(0))
        // timedelta(milliseconds=1)
        for session_id, periods in active_periods.items()
    }

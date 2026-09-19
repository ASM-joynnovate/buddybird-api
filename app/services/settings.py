from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.errors import UserSaveUnavailableError
from app.models import User, UserSetting
from app.schemas.settings import (
    NotificationSettingsDTO,
    SettingsDTO,
    SleepSettingsDTO,
    UpdateNotificationSettingsRequest,
    UpdateSleepSettingsRequest,
)


def build_settings_dto(setting: UserSetting) -> SettingsDTO:
    return SettingsDTO(
        sleep=SleepSettingsDTO(sleep_at=setting.sleep_at, wake_at=setting.wake_at),
        notifications=NotificationSettingsDTO(
            emergency=setting.notify_emergency,
            mimicry=setting.notify_mimicry,
            daily_summary=setting.notify_daily_summary,
            streak=setting.notify_streak,
            station_disconnect=setting.notify_station_disconnect,
        ),
    )


async def get_or_create_settings(*, db: AsyncSession, user: User) -> UserSetting:
    setting = await db.get(UserSetting, user.id)

    if setting is None:
        await db.execute(
            insert(UserSetting).values(user_id=user.id).on_conflict_do_nothing(index_elements=[UserSetting.user_id])
        )
        setting = await db.get(UserSetting, user.id)

    return setting


@transactional(unavailable_error=UserSaveUnavailableError)
async def get_settings(*, db: AsyncSession, user: User) -> SettingsDTO:
    return build_settings_dto(await get_or_create_settings(db=db, user=user))


@transactional(unavailable_error=UserSaveUnavailableError)
async def update_sleep(*, db: AsyncSession, user: User, data: UpdateSleepSettingsRequest) -> SettingsDTO:
    setting = await get_or_create_settings(db=db, user=user)

    setting.sleep_at = data.sleep_at
    setting.wake_at = data.wake_at

    await db.flush()

    return build_settings_dto(setting)


@transactional(unavailable_error=UserSaveUnavailableError)
async def update_notifications(*, db: AsyncSession, user: User, data: UpdateNotificationSettingsRequest) -> SettingsDTO:
    setting = await get_or_create_settings(db=db, user=user)

    setting.notify_emergency = data.emergency
    setting.notify_mimicry = data.mimicry
    setting.notify_daily_summary = data.daily_summary
    setting.notify_streak = data.streak
    setting.notify_station_disconnect = data.station_disconnect

    await db.flush()

    return build_settings_dto(setting)

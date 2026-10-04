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
            notice_enabled=setting.notice_notification_enabled,
            report_enabled=setting.report_notification_enabled,
            marketing_enabled=setting.marketing_notification_enabled,
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
    setting = await get_or_create_settings(db=db, user=user)

    return build_settings_dto(setting)


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

    setting.notice_notification_enabled = data.notice_enabled
    setting.report_notification_enabled = data.report_enabled
    setting.marketing_notification_enabled = data.marketing_enabled

    await db.flush()

    return build_settings_dto(setting)

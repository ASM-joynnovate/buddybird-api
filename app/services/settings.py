from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import ConsentStatusEnum
from app.errors import ResourceNotFoundError, UserSaveUnavailableError
from app.models import Consent, User, UserConsent, UserSetting
from app.schemas.settings import (
    NotificationSettingsDTO,
    SettingsDTO,
    SleepSettingsDTO,
    UpdateNotificationSettingsRequest,
    UpdateSleepSettingsRequest,
)


def build_settings_dto(setting: UserSetting, marketing_enabled: bool) -> SettingsDTO:
    return SettingsDTO(
        sleep=SleepSettingsDTO(sleep_at=setting.sleep_at, wake_at=setting.wake_at),
        notifications=NotificationSettingsDTO(
            notice_enabled=setting.notice_notification_enabled,
            report_enabled=setting.report_notification_enabled,
            marketing_enabled=marketing_enabled,
        ),
    )


async def get_marketing_consent(*, db: AsyncSession, user: User) -> tuple[Consent | None, str | None]:
    stmt = (
        select(Consent)
        .where(Consent.kind == "marketing", Consent.published_at <= datetime.now(UTC))
        .order_by(Consent.version.desc())
        .limit(1)
    )
    consent = await db.scalar(stmt)

    if consent is None:
        return None, None

    stmt = select(UserConsent.status).where(UserConsent.user_id == user.id, UserConsent.consent_id == consent.id)
    status = await db.scalar(stmt)

    return consent, status


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
    _, status = await get_marketing_consent(db=db, user=user)

    return build_settings_dto(setting, status == ConsentStatusEnum.GRANTED.value)


@transactional(unavailable_error=UserSaveUnavailableError)
async def update_sleep(*, db: AsyncSession, user: User, data: UpdateSleepSettingsRequest) -> SettingsDTO:
    setting = await get_or_create_settings(db=db, user=user)

    setting.sleep_at = data.sleep_at
    setting.wake_at = data.wake_at

    await db.flush()

    _, status = await get_marketing_consent(db=db, user=user)

    return build_settings_dto(setting, status == ConsentStatusEnum.GRANTED.value)


@transactional(unavailable_error=UserSaveUnavailableError)
async def update_notifications(*, db: AsyncSession, user: User, data: UpdateNotificationSettingsRequest) -> SettingsDTO:
    setting = await get_or_create_settings(db=db, user=user)
    consent, current_status = await get_marketing_consent(db=db, user=user)

    setting.notice_notification_enabled = data.notice_enabled
    setting.report_notification_enabled = data.report_enabled

    if data.marketing_enabled != (current_status == ConsentStatusEnum.GRANTED.value):
        if consent is None:
            raise ResourceNotFoundError

        decided_at = datetime.now(UTC)
        status = ConsentStatusEnum.GRANTED.value if data.marketing_enabled else ConsentStatusEnum.DENIED.value

        await db.execute(
            insert(UserConsent)
            .values(user_id=user.id, consent_id=consent.id, status=status, decided_at=decided_at)
            .on_conflict_do_update(
                index_elements=[UserConsent.user_id, UserConsent.consent_id],
                set_={"status": status, "decided_at": decided_at},
            )
        )

    await db.flush()

    return build_settings_dto(setting, data.marketing_enabled)

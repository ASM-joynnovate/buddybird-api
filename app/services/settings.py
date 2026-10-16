from datetime import UTC, datetime

from pydantic.experimental.missing_sentinel import MISSING
from sqlalchemy import and_, func, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_or_404, transactional
from app.enums import LocaleEnum, NotificationSettingKindEnum
from app.errors import (
    DuplicateNotificationSettingKindError,
    NotificationSettingSaveUnavailableError,
    UserSaveUnavailableError,
)
from app.models import (
    I18n,
    NotificationSettingGroup,
    NotificationSettingItem,
    User,
    UserNotificationSetting,
    UserSetting,
)
from app.schemas.base import I18nDTO
from app.schemas.settings import (
    BackofficeNotificationSettingGroupDTO,
    BackofficeNotificationSettingItemDTO,
    BackofficeUserNotificationSettingGroupDTO,
    BackofficeUserNotificationSettingItemDTO,
    BackofficeUserNotificationSettingListDTO,
    CreateNotificationSettingGroupRequest,
    CreateNotificationSettingItemRequest,
    NotificationSettingGroupDTO,
    NotificationSettingItemDTO,
    NotificationSettingListDTO,
    NotificationSettingsDTO,
    SaveUserNotificationSettingRequest,
    SettingsDTO,
    SleepSettingsDTO,
    UpdateNotificationSettingGroupRequest,
    UpdateNotificationSettingItemRequest,
    UpdateNotificationSettingsRequest,
    UpdatePushSettingRequest,
    UpdateSleepSettingsRequest,
)

ITEM_ENABLED = {
    kind: func.coalesce(
        select(UserNotificationSetting.is_enabled)
        .join(NotificationSettingItem, NotificationSettingItem.id == UserNotificationSetting.item_id)
        .where(UserNotificationSetting.user_id == User.id, NotificationSettingItem.kind == kind.value)
        .correlate(User)
        .scalar_subquery(),
        select(NotificationSettingItem.default_enabled)
        .where(NotificationSettingItem.kind == kind.value)
        .scalar_subquery(),
    )
    for kind in NotificationSettingKindEnum
}


async def build_settings_dto(*, db: AsyncSession, setting: UserSetting) -> SettingsDTO:
    stmt = select(
        NotificationSettingItem.kind,
        func.coalesce(UserNotificationSetting.is_enabled, NotificationSettingItem.default_enabled),
    ).outerjoin(
        UserNotificationSetting,
        and_(
            UserNotificationSetting.item_id == NotificationSettingItem.id,
            UserNotificationSetting.user_id == setting.user_id,
        ),
    )
    enabled = dict((await db.execute(stmt)).all())

    return SettingsDTO(
        sleep=SleepSettingsDTO(sleep_at=setting.sleep_at, wake_at=setting.wake_at),
        notifications=NotificationSettingsDTO(
            push_enabled=setting.push_notification_enabled,
            announcement_enabled=enabled[NotificationSettingKindEnum.ANNOUNCEMENT],
            report_enabled=enabled[NotificationSettingKindEnum.REPORT],
            emergency_enabled=enabled[NotificationSettingKindEnum.EMERGENCY],
            marketing_enabled=enabled[NotificationSettingKindEnum.MARKETING],
            marketing_night_enabled=enabled[NotificationSettingKindEnum.MARKETING_NIGHT],
        ),
    )


async def build_notification_setting_list_dto(
    *, db: AsyncSession, user: User, setting: UserSetting, locale: LocaleEnum
) -> NotificationSettingListDTO:
    stmt = (
        select(
            NotificationSettingItem,
            func.coalesce(UserNotificationSetting.is_enabled, NotificationSettingItem.default_enabled),
        )
        .outerjoin(
            UserNotificationSetting,
            and_(
                UserNotificationSetting.item_id == NotificationSettingItem.id,
                UserNotificationSetting.user_id == user.id,
            ),
        )
        .order_by(NotificationSettingItem.sort_order)
    )
    rows = (await db.execute(stmt)).all()

    stmt = select(NotificationSettingGroup).order_by(NotificationSettingGroup.sort_order)
    groups = (await db.scalars(stmt)).all()

    items = [
        (
            item.group_id,
            NotificationSettingItemDTO(
                id=item.id,
                kind=item.kind,
                title=item.title_i18n.get_text(locale),
                description=item.description_i18n.get_text(locale) if item.description_i18n is not None else None,
                enabled=enabled,
            ),
        )
        for item, enabled in rows
    ]

    return NotificationSettingListDTO(
        push_enabled=setting.push_notification_enabled,
        groups=[
            NotificationSettingGroupDTO(
                id=group.id,
                title=group.title_i18n.get_text(locale),
                description=group.description_i18n.get_text(locale) if group.description_i18n is not None else None,
                items=[dto for group_id, dto in items if group_id == group.id],
            )
            for group in groups
        ],
        items=[dto for group_id, dto in items if group_id is None],
    )


def build_backoffice_notification_setting_group_dto(
    group: NotificationSettingGroup,
) -> BackofficeNotificationSettingGroupDTO:
    return BackofficeNotificationSettingGroupDTO(
        id=group.id,
        title=I18nDTO.model_validate(group.title_i18n, from_attributes=True),
        description=I18nDTO.model_validate(group.description_i18n, from_attributes=True)
        if group.description_i18n is not None
        else None,
        sort_order=group.sort_order,
    )


def build_backoffice_notification_setting_item_dto(
    item: NotificationSettingItem,
) -> BackofficeNotificationSettingItemDTO:
    return BackofficeNotificationSettingItemDTO(
        id=item.id,
        group_id=item.group_id,
        kind=item.kind,
        title=I18nDTO.model_validate(item.title_i18n, from_attributes=True),
        description=I18nDTO.model_validate(item.description_i18n, from_attributes=True)
        if item.description_i18n is not None
        else None,
        default_enabled=item.default_enabled,
        sort_order=item.sort_order,
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

    return await build_settings_dto(db=db, setting=setting)


@transactional(unavailable_error=UserSaveUnavailableError)
async def update_sleep(*, db: AsyncSession, user: User, data: UpdateSleepSettingsRequest) -> SettingsDTO:
    setting = await get_or_create_settings(db=db, user=user)

    setting.sleep_at = data.sleep_at
    setting.wake_at = data.wake_at

    await db.flush()

    return await build_settings_dto(db=db, setting=setting)


@transactional(unavailable_error=UserSaveUnavailableError)
async def update_notifications(*, db: AsyncSession, user: User, data: UpdateNotificationSettingsRequest) -> SettingsDTO:
    setting = await get_or_create_settings(db=db, user=user)

    setting.push_notification_enabled = data.push_enabled

    values = {
        NotificationSettingKindEnum.ANNOUNCEMENT: data.announcement_enabled,
        NotificationSettingKindEnum.REPORT: data.report_enabled,
        NotificationSettingKindEnum.MARKETING: data.marketing_enabled,
        NotificationSettingKindEnum.MARKETING_NIGHT: data.marketing_night_enabled,
    }

    if data.emergency_enabled is not MISSING:
        values[NotificationSettingKindEnum.EMERGENCY] = data.emergency_enabled

    stmt = select(NotificationSettingItem.id, NotificationSettingItem.kind).where(
        NotificationSettingItem.kind.in_(values)
    )
    items = (await db.execute(stmt)).all()

    decided_at = datetime.now(UTC)
    stmt = insert(UserNotificationSetting).values(
        [
            {"user_id": user.id, "item_id": item_id, "is_enabled": values[kind], "decided_at": decided_at}
            for item_id, kind in items
        ]
    )

    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=[UserNotificationSetting.user_id, UserNotificationSetting.item_id],
            set_={"is_enabled": stmt.excluded.is_enabled, "decided_at": stmt.excluded.decided_at},
            where=UserNotificationSetting.is_enabled != stmt.excluded.is_enabled,
        )
    )
    await db.flush()

    return await build_settings_dto(db=db, setting=setting)


@transactional(unavailable_error=UserSaveUnavailableError)
async def get_notification_settings(*, db: AsyncSession, user: User, locale: LocaleEnum) -> NotificationSettingListDTO:
    setting = await get_or_create_settings(db=db, user=user)

    return await build_notification_setting_list_dto(db=db, user=user, setting=setting, locale=locale)


@transactional(unavailable_error=UserSaveUnavailableError)
async def update_push(
    *, db: AsyncSession, user: User, data: UpdatePushSettingRequest, locale: LocaleEnum
) -> NotificationSettingListDTO:
    setting = await get_or_create_settings(db=db, user=user)

    setting.push_notification_enabled = data.push_enabled

    await db.flush()

    return await build_notification_setting_list_dto(db=db, user=user, setting=setting, locale=locale)


@transactional(unavailable_error=UserSaveUnavailableError)
async def save_notification_setting(
    *,
    db: AsyncSession,
    user: User,
    item: NotificationSettingItem,
    data: SaveUserNotificationSettingRequest,
    locale: LocaleEnum,
) -> NotificationSettingListDTO:
    setting = await get_or_create_settings(db=db, user=user)

    stmt = insert(UserNotificationSetting).values(
        user_id=user.id, item_id=item.id, is_enabled=data.enabled, decided_at=datetime.now(UTC)
    )

    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=[UserNotificationSetting.user_id, UserNotificationSetting.item_id],
            set_={"is_enabled": stmt.excluded.is_enabled, "decided_at": stmt.excluded.decided_at},
            where=UserNotificationSetting.is_enabled != stmt.excluded.is_enabled,
        )
    )

    return await build_notification_setting_list_dto(db=db, user=user, setting=setting, locale=locale)


async def get_backoffice_notification_setting_groups(
    *, db: AsyncSession
) -> list[BackofficeNotificationSettingGroupDTO]:
    stmt = select(NotificationSettingGroup).order_by(NotificationSettingGroup.sort_order)
    groups = (await db.scalars(stmt)).all()

    return [build_backoffice_notification_setting_group_dto(group) for group in groups]


async def get_backoffice_notification_setting_items(*, db: AsyncSession) -> list[BackofficeNotificationSettingItemDTO]:
    stmt = select(NotificationSettingItem).order_by(NotificationSettingItem.sort_order)
    items = (await db.scalars(stmt)).all()

    return [build_backoffice_notification_setting_item_dto(item) for item in items]


async def get_backoffice_user_notification_settings(
    *, db: AsyncSession, user: User
) -> BackofficeUserNotificationSettingListDTO:
    stmt = select(
        func.coalesce(
            select(UserSetting.push_notification_enabled).where(UserSetting.user_id == user.id).scalar_subquery(),
            true(),
        )
    )
    push_enabled = await db.scalar(stmt)

    stmt = (
        select(
            NotificationSettingItem,
            func.coalesce(UserNotificationSetting.is_enabled, NotificationSettingItem.default_enabled),
            UserNotificationSetting.decided_at,
        )
        .outerjoin(
            UserNotificationSetting,
            and_(
                UserNotificationSetting.item_id == NotificationSettingItem.id,
                UserNotificationSetting.user_id == user.id,
            ),
        )
        .order_by(NotificationSettingItem.sort_order)
    )
    rows = (await db.execute(stmt)).all()

    stmt = select(NotificationSettingGroup).order_by(NotificationSettingGroup.sort_order)
    groups = (await db.scalars(stmt)).all()

    items = [
        (
            item.group_id,
            BackofficeUserNotificationSettingItemDTO(
                id=item.id,
                kind=item.kind,
                title=I18nDTO.model_validate(item.title_i18n, from_attributes=True),
                description=I18nDTO.model_validate(item.description_i18n, from_attributes=True)
                if item.description_i18n is not None
                else None,
                enabled=enabled,
                decided_at=decided_at,
            ),
        )
        for item, enabled, decided_at in rows
    ]

    return BackofficeUserNotificationSettingListDTO(
        push_enabled=push_enabled,
        groups=[
            BackofficeUserNotificationSettingGroupDTO(
                id=group.id,
                title=I18nDTO.model_validate(group.title_i18n, from_attributes=True),
                description=I18nDTO.model_validate(group.description_i18n, from_attributes=True)
                if group.description_i18n is not None
                else None,
                items=[dto for group_id, dto in items if group_id == group.id],
            )
            for group in groups
        ],
        items=[dto for group_id, dto in items if group_id is None],
    )


@transactional(unavailable_error=NotificationSettingSaveUnavailableError)
async def create_notification_setting_group(
    *, db: AsyncSession, data: CreateNotificationSettingGroupRequest
) -> BackofficeNotificationSettingGroupDTO:
    group = NotificationSettingGroup(
        title_i18n=I18n(**data.title.model_dump()),
        description_i18n=I18n(**data.description.model_dump()) if data.description is not None else None,
        sort_order=data.sort_order,
    )

    db.add(group)
    await db.flush()

    return build_backoffice_notification_setting_group_dto(group)


@transactional(unavailable_error=NotificationSettingSaveUnavailableError)
async def update_notification_setting_group(
    *, db: AsyncSession, group: NotificationSettingGroup, data: UpdateNotificationSettingGroupRequest
) -> BackofficeNotificationSettingGroupDTO:
    if data.title is not MISSING:
        for name, value in data.title.model_dump(exclude_unset=True).items():
            setattr(group.title_i18n, name, value)

    if data.description is not MISSING:
        group.description_i18n = I18n(**data.description.model_dump()) if data.description is not None else None

    for name, value in data.model_dump(exclude_unset=True, exclude={"title", "description"}).items():
        setattr(group, name, value)

    await db.flush()

    return build_backoffice_notification_setting_group_dto(group)


@transactional(unavailable_error=NotificationSettingSaveUnavailableError)
async def create_notification_setting_item(
    *, db: AsyncSession, data: CreateNotificationSettingItemRequest
) -> BackofficeNotificationSettingItemDTO:
    if data.group_id is not None:
        await get_or_404(db=db, model=NotificationSettingGroup, id=data.group_id)

    item = NotificationSettingItem(
        group_id=data.group_id,
        kind=data.kind.value,
        title_i18n=I18n(**data.title.model_dump()),
        description_i18n=I18n(**data.description.model_dump()) if data.description is not None else None,
        default_enabled=data.default_enabled,
        sort_order=data.sort_order,
    )

    db.add(item)

    try:
        await db.flush()
    except IntegrityError as exc:
        raise DuplicateNotificationSettingKindError from exc

    return build_backoffice_notification_setting_item_dto(item)


@transactional(unavailable_error=NotificationSettingSaveUnavailableError)
async def update_notification_setting_item(
    *, db: AsyncSession, item: NotificationSettingItem, data: UpdateNotificationSettingItemRequest
) -> BackofficeNotificationSettingItemDTO:
    if data.group_id is not MISSING and data.group_id is not None:
        await get_or_404(db=db, model=NotificationSettingGroup, id=data.group_id)

    if data.title is not MISSING:
        for name, value in data.title.model_dump(exclude_unset=True).items():
            setattr(item.title_i18n, name, value)

    if data.description is not MISSING:
        item.description_i18n = I18n(**data.description.model_dump()) if data.description is not None else None

    for name, value in data.model_dump(exclude_unset=True, exclude={"title", "description"}).items():
        setattr(item, name, value)

    await db.flush()

    return build_backoffice_notification_setting_item_dto(item)

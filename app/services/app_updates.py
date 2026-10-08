from pydantic.experimental.missing_sentinel import MISSING
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import LocaleEnum, PlatformEnum
from app.errors import AppUpdateSaveUnavailableError, DuplicateAppUpdateVersionError, ResourceNotFoundError
from app.models import AppUpdate, I18n
from app.schemas.app_updates import (
    AppUpdateDTO,
    AppUpdateLatestDTO,
    AppUpdateMinSupportedDTO,
    BackofficeAppUpdateDTO,
    BackofficeAppUpdateListParams,
    CreateAppUpdateRequest,
    UpdateAppUpdateRequest,
)
from app.schemas.base import I18nDTO
from app.services.devices import APP_UPDATE_VERSION_NUMBERS, MIN_SUPPORTED_APP_UPDATE


def build_backoffice_app_update_dto(app_update: AppUpdate) -> BackofficeAppUpdateDTO:
    release_notes = None

    if app_update.release_notes_i18n is not None:
        release_notes = I18nDTO(ko_kr=app_update.release_notes_i18n.ko_kr, en_us=app_update.release_notes_i18n.en_us)

    return BackofficeAppUpdateDTO(
        id=app_update.id,
        platform=PlatformEnum(app_update.platform),
        version=app_update.version,
        is_forced=app_update.is_forced,
        release_notes=release_notes,
        created_at=app_update.created_at,
    )


async def get_detail(*, db: AsyncSession, platform: PlatformEnum, locale: LocaleEnum) -> AppUpdateDTO:
    stmt = (
        select(AppUpdate)
        .where(AppUpdate.platform == platform.value)
        .order_by(APP_UPDATE_VERSION_NUMBERS.desc())
        .limit(1)
    )
    app_update = await db.scalar(stmt)

    if app_update is None:
        raise ResourceNotFoundError

    stmt = select(MIN_SUPPORTED_APP_UPDATE.c.version).where(MIN_SUPPORTED_APP_UPDATE.c.platform == platform.value)
    min_supported_version = await db.scalar(stmt)

    release_notes = []

    if app_update.release_notes_i18n is not None:
        release_notes = app_update.release_notes_i18n.get_text(locale).splitlines()

    return AppUpdateDTO(
        latest=AppUpdateLatestDTO(version=app_update.version, release_notes=release_notes),
        min_supported=AppUpdateMinSupportedDTO(version=min_supported_version or "0.0.0"),
    )


async def get_backoffice_list(
    *, db: AsyncSession, query: BackofficeAppUpdateListParams
) -> list[BackofficeAppUpdateDTO]:
    stmt = (
        select(AppUpdate).where(AppUpdate.platform == query.platform.value).order_by(APP_UPDATE_VERSION_NUMBERS.desc())
    )
    app_updates = (await db.scalars(stmt)).all()

    return [build_backoffice_app_update_dto(app_update) for app_update in app_updates]


@transactional(unavailable_error=AppUpdateSaveUnavailableError)
async def create(*, db: AsyncSession, data: CreateAppUpdateRequest) -> BackofficeAppUpdateDTO:
    release_notes_i18n = None

    if data.release_notes is not None:
        release_notes_i18n = I18n(ko_kr=data.release_notes.ko_kr, en_us=data.release_notes.en_us)

    app_update = AppUpdate(
        platform=data.platform.value,
        version=data.version,
        is_forced=data.is_forced,
        release_notes_i18n=release_notes_i18n,
    )

    db.add(app_update)

    try:
        await db.flush()
    except IntegrityError as exc:
        raise DuplicateAppUpdateVersionError from exc

    return build_backoffice_app_update_dto(app_update)


@transactional(unavailable_error=AppUpdateSaveUnavailableError)
async def update(*, db: AsyncSession, app_update: AppUpdate, data: UpdateAppUpdateRequest) -> BackofficeAppUpdateDTO:
    if data.release_notes is None:
        app_update.release_notes_i18n = None
    elif data.release_notes is not MISSING and app_update.release_notes_i18n is not None:
        app_update.release_notes_i18n.ko_kr = data.release_notes.ko_kr
        app_update.release_notes_i18n.en_us = data.release_notes.en_us
    elif data.release_notes is not MISSING:
        app_update.release_notes_i18n = I18n(ko_kr=data.release_notes.ko_kr, en_us=data.release_notes.en_us)

    for name, value in data.model_dump(exclude_unset=True, exclude={"release_notes"}).items():
        setattr(app_update, name, value)

    try:
        await db.flush()
    except IntegrityError as exc:
        raise DuplicateAppUpdateVersionError from exc

    return build_backoffice_app_update_dto(app_update)

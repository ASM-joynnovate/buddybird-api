from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import LocaleEnum, PlatformEnum
from app.errors import AppUpdateSaveUnavailableError, ResourceNotFoundError
from app.models import AppUpdate, I18n
from app.schemas.app_updates import (
    AppUpdateDTO,
    AppUpdateLatestDTO,
    AppUpdateMinSupportedDTO,
    BackofficeAppUpdateDTO,
    BackofficeAppUpdateHistoryDTO,
    BackofficeAppUpdateLatestDTO,
    SaveAppUpdateRequest,
)
from app.schemas.base import I18nDTO


def build_backoffice_app_update_dto(app_update: AppUpdate) -> BackofficeAppUpdateDTO:
    release_notes = None

    if app_update.release_notes_i18n is not None:
        release_notes = I18nDTO(ko_kr=app_update.release_notes_i18n.ko_kr, en_us=app_update.release_notes_i18n.en_us)

    return BackofficeAppUpdateDTO(
        latest=BackofficeAppUpdateLatestDTO(version=app_update.latest_version, release_notes=release_notes),
        min_supported=AppUpdateMinSupportedDTO(version=app_update.min_supported_version),
    )


async def get_detail(*, db: AsyncSession, platform: PlatformEnum, locale: LocaleEnum) -> AppUpdateDTO:
    stmt = select(AppUpdate).where(AppUpdate.platform == platform.value).order_by(AppUpdate.created_at.desc()).limit(1)
    app_update = await db.scalar(stmt)

    if app_update is None:
        raise ResourceNotFoundError

    release_notes = []

    if app_update.release_notes_i18n is not None:
        release_notes = app_update.release_notes_i18n.get_text(locale).splitlines()

    return AppUpdateDTO(
        latest=AppUpdateLatestDTO(version=app_update.latest_version, release_notes=release_notes),
        min_supported=AppUpdateMinSupportedDTO(version=app_update.min_supported_version),
    )


async def get_backoffice_detail(*, db: AsyncSession, platform: PlatformEnum) -> BackofficeAppUpdateDTO:
    stmt = select(AppUpdate).where(AppUpdate.platform == platform.value).order_by(AppUpdate.created_at.desc()).limit(1)
    app_update = await db.scalar(stmt)

    if app_update is None:
        raise ResourceNotFoundError

    return build_backoffice_app_update_dto(app_update)


async def get_backoffice_history(*, db: AsyncSession, platform: PlatformEnum) -> list[BackofficeAppUpdateHistoryDTO]:
    stmt = select(AppUpdate).where(AppUpdate.platform == platform.value).order_by(AppUpdate.created_at.desc())
    app_updates = (await db.scalars(stmt)).all()

    return [
        BackofficeAppUpdateHistoryDTO(
            **build_backoffice_app_update_dto(app_update).model_dump(),
            created_at=app_update.created_at,
        )
        for app_update in app_updates
    ]


@transactional(unavailable_error=AppUpdateSaveUnavailableError)
async def save(*, db: AsyncSession, platform: PlatformEnum, data: SaveAppUpdateRequest) -> BackofficeAppUpdateDTO:
    release_notes_i18n = None

    if data.latest.release_notes is not None:
        release_notes_i18n = I18n(ko_kr=data.latest.release_notes.ko_kr, en_us=data.latest.release_notes.en_us)

    app_update = AppUpdate(
        platform=platform.value,
        latest_version=data.latest.version,
        min_supported_version=data.min_supported.version,
        release_notes_i18n=release_notes_i18n,
    )

    db.add(app_update)
    await db.flush()

    return build_backoffice_app_update_dto(app_update)

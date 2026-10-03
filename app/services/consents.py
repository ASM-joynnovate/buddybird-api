from datetime import UTC, datetime

from pydantic.experimental.missing_sentinel import MISSING
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import LocaleEnum
from app.errors import ConsentAlreadyPublishedError, ConsentSaveUnavailableError
from app.models import Consent, I18n, User, UserConsent
from app.schemas.base import I18nDTO
from app.schemas.consents import BackofficeConsentDTO, ConsentDTO, CreateConsentRequest, UpdateConsentRequest


def build_consent_dto(consent: Consent, status: str | None, locale: LocaleEnum) -> ConsentDTO:
    return ConsentDTO(
        id=consent.id,
        kind=consent.kind,
        version=consent.version,
        title=consent.title_i18n.get_text(locale),
        body=consent.body_i18n.get_text(locale),
        is_required=consent.is_required,
        published_at=consent.published_at,
        status=status,
    )


def build_backoffice_consent_dto(consent: Consent) -> BackofficeConsentDTO:
    return BackofficeConsentDTO(
        id=consent.id,
        kind=consent.kind,
        version=consent.version,
        title=I18nDTO(ko_kr=consent.title_i18n.ko_kr, en_us=consent.title_i18n.en_us),
        body=I18nDTO(ko_kr=consent.body_i18n.ko_kr, en_us=consent.body_i18n.en_us),
        is_required=consent.is_required,
        published_at=consent.published_at,
    )


async def get_list(*, db: AsyncSession, user: User, locale: LocaleEnum) -> list[ConsentDTO]:
    now = datetime.now(UTC)
    latest_ids = (
        select(Consent.id)
        .where(Consent.published_at <= now)
        .distinct(Consent.kind)
        .order_by(Consent.kind, Consent.version.desc())
        .scalar_subquery()
    )
    stmt = (
        select(Consent, UserConsent.status)
        .outerjoin(UserConsent, and_(UserConsent.consent_id == Consent.id, UserConsent.user_id == user.id))
        .where(Consent.id.in_(latest_ids))
        .order_by(Consent.kind)
    )
    rows = (await db.execute(stmt)).all()

    return [build_consent_dto(consent, status, locale) for consent, status in rows]


async def get_detail(*, db: AsyncSession, user: User, locale: LocaleEnum, consent: Consent) -> ConsentDTO:
    status = await db.scalar(
        select(UserConsent.status).where(UserConsent.consent_id == consent.id, UserConsent.user_id == user.id)
    )

    return build_consent_dto(consent, status, locale)


@transactional(unavailable_error=ConsentSaveUnavailableError)
async def create(*, db: AsyncSession, data: CreateConsentRequest) -> BackofficeConsentDTO:
    latest_version = await db.scalar(
        select(func.max(Consent.version)).where(Consent.kind == data.kind).execution_options(include_deleted=True)
    )
    consent = Consent(
        kind=data.kind,
        version=(latest_version or 0) + 1,
        title_i18n=I18n(ko_kr=data.title.ko_kr, en_us=data.title.en_us),
        body_i18n=I18n(ko_kr=data.body.ko_kr, en_us=data.body.en_us),
        is_required=data.is_required,
        published_at=data.published_at,
        is_deleted=False,
    )

    db.add(consent)
    await db.flush()

    return build_backoffice_consent_dto(consent)


@transactional(unavailable_error=ConsentSaveUnavailableError)
async def update(*, db: AsyncSession, consent: Consent, data: UpdateConsentRequest) -> BackofficeConsentDTO:
    if consent.published_at <= datetime.now(UTC):
        raise ConsentAlreadyPublishedError

    if data.title is not MISSING:
        for name, value in data.title.model_dump(exclude_unset=True).items():
            setattr(consent.title_i18n, name, value)

    if data.body is not MISSING:
        for name, value in data.body.model_dump(exclude_unset=True).items():
            setattr(consent.body_i18n, name, value)

    for name, value in data.model_dump(exclude_unset=True, exclude={"title", "body"}).items():
        setattr(consent, name, value)

    await db.flush()

    return build_backoffice_consent_dto(consent)


@transactional(unavailable_error=ConsentSaveUnavailableError)
async def delete(*, db: AsyncSession, consent: Consent) -> None:
    if consent.published_at <= datetime.now(UTC):
        raise ConsentAlreadyPublishedError

    consent.is_deleted = True

    await db.flush()

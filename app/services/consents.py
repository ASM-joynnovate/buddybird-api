from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.errors import ConsentAlreadyPublishedError, ConsentSaveUnavailableError
from app.models import Consent, User, UserConsent
from app.schemas.consents import ConsentDTO, CreateConsentRequest, UpdateConsentRequest


def build_consent_dto(consent: Consent, status: str | None) -> ConsentDTO:
    return ConsentDTO(
        id=consent.id,
        kind=consent.kind,
        version=consent.version,
        title=consent.title,
        body=consent.body,
        is_required=consent.is_required,
        published_at=consent.published_at,
        status=status,
    )


async def get_list(*, db: AsyncSession, user: User) -> list[ConsentDTO]:
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

    return [build_consent_dto(consent, status) for consent, status in rows]


async def get_detail(*, db: AsyncSession, user: User, consent: Consent) -> ConsentDTO:
    status = await db.scalar(
        select(UserConsent.status).where(UserConsent.consent_id == consent.id, UserConsent.user_id == user.id)
    )

    return build_consent_dto(consent, status)


@transactional(unavailable_error=ConsentSaveUnavailableError)
async def create(*, db: AsyncSession, data: CreateConsentRequest) -> ConsentDTO:
    latest_version = await db.scalar(
        select(func.max(Consent.version)).where(Consent.kind == data.kind).execution_options(include_deleted=True)
    )
    consent = Consent(
        kind=data.kind,
        version=(latest_version or 0) + 1,
        title=data.title,
        body=data.body,
        is_required=data.is_required,
        published_at=data.published_at,
        is_deleted=False,
    )

    db.add(consent)
    await db.flush()

    return build_consent_dto(consent, None)


@transactional(unavailable_error=ConsentSaveUnavailableError)
async def update(*, db: AsyncSession, consent: Consent, data: UpdateConsentRequest) -> ConsentDTO:
    if consent.published_at <= datetime.now(UTC):
        raise ConsentAlreadyPublishedError

    changes = data.model_dump(exclude_unset=True)

    if "title" in changes:
        consent.title = changes["title"]

    if "body" in changes:
        consent.body = changes["body"]

    if "is_required" in changes:
        consent.is_required = changes["is_required"]

    if "published_at" in changes:
        consent.published_at = changes["published_at"]

    await db.flush()

    return build_consent_dto(consent, None)


@transactional(unavailable_error=ConsentSaveUnavailableError)
async def delete(*, db: AsyncSession, consent: Consent) -> None:
    if consent.published_at <= datetime.now(UTC):
        raise ConsentAlreadyPublishedError

    consent.is_deleted = True

    await db.flush()

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_or_404, transactional
from app.errors import ConsentSaveUnavailableError, ResourceNotFoundError
from app.models import Consent, User, UserConsent
from app.schemas.consents import SaveUserConsentRequest, UserConsentDTO


def build_user_consent_dto(user_consent: UserConsent) -> UserConsentDTO:
    return UserConsentDTO(
        consent_id=user_consent.consent_id,
        kind=user_consent.consent.kind,
        version=user_consent.consent.version,
        status=user_consent.status,
        decided_at=user_consent.decided_at,
    )


async def get_list(*, db: AsyncSession, user: User) -> list[UserConsentDTO]:
    stmt = (
        select(UserConsent)
        .join(Consent, Consent.id == UserConsent.consent_id)
        .where(UserConsent.user_id == user.id)
        .order_by(Consent.kind, Consent.version)
    )
    user_consents = (await db.scalars(stmt)).all()

    return [build_user_consent_dto(user_consent) for user_consent in user_consents]


@transactional(unavailable_error=ConsentSaveUnavailableError)
async def save(*, db: AsyncSession, user: User, data: SaveUserConsentRequest) -> UserConsentDTO:
    consent = await get_or_404(db=db, model=Consent, id=data.consent_id)

    if consent.published_at > datetime.now(UTC):
        raise ResourceNotFoundError

    decided_at = datetime.now(UTC)
    user_consent = (
        await db.scalars(
            insert(UserConsent)
            .values(user_id=user.id, consent_id=consent.id, status=data.status.value, decided_at=decided_at)
            .on_conflict_do_update(
                index_elements=[UserConsent.user_id, UserConsent.consent_id],
                set_={"status": data.status.value, "decided_at": decided_at},
            )
            .returning(UserConsent)
        )
    ).one()

    return build_user_consent_dto(user_consent)

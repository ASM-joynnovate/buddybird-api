from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.errors import UserSaveUnavailableError
from app.models import User, UserConsent
from app.schemas.consents import ConsentDTO, SaveConsentRequest


async def get_consents(*, db: AsyncSession, user: User) -> list[ConsentDTO]:
    consents = (
        await db.scalars(
            select(UserConsent)
            .where(UserConsent.user_id == user.id)
            .order_by(UserConsent.kind, UserConsent.notice_version)
        )
    ).all()

    return [
        ConsentDTO(
            kind=consent.kind,
            notice_version=consent.notice_version,
            status=consent.status,
            decided_at=consent.decided_at,
        )
        for consent in consents
    ]


@transactional(unavailable_error=UserSaveUnavailableError)
async def save_consent(*, db: AsyncSession, user: User, data: SaveConsentRequest) -> ConsentDTO:
    decided_at = datetime.now(UTC)
    consent = (
        await db.scalars(
            insert(UserConsent)
            .values(
                user_id=user.id,
                kind=data.kind.value,
                notice_version=data.notice_version,
                status=data.status.value,
                decided_at=decided_at,
            )
            .on_conflict_do_update(
                index_elements=[UserConsent.user_id, UserConsent.kind, UserConsent.notice_version],
                set_={"status": data.status.value, "decided_at": decided_at},
            )
            .returning(UserConsent)
        )
    ).one()

    return ConsentDTO(
        kind=consent.kind,
        notice_version=consent.notice_version,
        status=consent.status,
        decided_at=consent.decided_at,
    )

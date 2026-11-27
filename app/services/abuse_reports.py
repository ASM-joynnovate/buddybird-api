from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_or_404, transactional
from app.errors import AbuseReportSaveUnavailableError, ResourceNotFoundError, SelfTargetError
from app.file import build_file_dto
from app.models import AbuseReport, FeedItem, Parrot, User
from app.r2 import R2StorageClient
from app.schemas.abuse_reports import (
    BackofficeAbuseReportDTO,
    BackofficeAbuseReportedUserDTO,
    BackofficeAbuseReportFeedItemDTO,
    BackofficeAbuseReportListParams,
    CreateAbuseReportRequest,
)
from app.schemas.parrots import BackofficeParrotDTO
from app.services.users import build_backoffice_user_dto


@transactional(unavailable_error=AbuseReportSaveUnavailableError)
async def create(*, db: AsyncSession, user: User, data: CreateAbuseReportRequest) -> None:
    if data.reported_user_id == user.id:
        raise SelfTargetError

    await get_or_404(db=db, model=User, id=data.reported_user_id)

    if data.feed_item_id is not None:
        stmt = select(FeedItem.id).where(FeedItem.id == data.feed_item_id, FeedItem.user_id == data.reported_user_id)

        if await db.scalar(stmt) is None:
            raise ResourceNotFoundError

    stmt = insert(AbuseReport).values(
        reporter_user_id=user.id,
        reported_user_id=data.reported_user_id,
        feed_item_id=data.feed_item_id,
        reason=data.reason,
        description=data.description,
    )

    await db.execute(stmt.on_conflict_do_nothing())


async def get_backoffice_list(
    *, db: AsyncSession, storage: R2StorageClient, query: BackofficeAbuseReportListParams
) -> tuple[list[BackofficeAbuseReportDTO], int]:
    stmt = select(AbuseReport)

    if query.is_handled is not None:
        stmt = stmt.where(AbuseReport.handled_at.is_not(None) if query.is_handled else AbuseReport.handled_at.is_(None))

    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    reports = (
        await db.scalars(
            stmt.order_by(AbuseReport.created_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    reported_user_ids = {report.reported_user_id for report in reports}
    user_ids = {report.reporter_user_id for report in reports} | reported_user_ids

    stmt = select(User).where(User.id.in_(user_ids)).execution_options(include_deleted=True)
    users = {user.id: user for user in (await db.scalars(stmt)).all()}

    stmt = select(Parrot).where(Parrot.user_id.in_(reported_user_ids)).order_by(Parrot.created_at)
    parrots = (await db.scalars(stmt)).all()

    reported_users = {
        user_id: BackofficeAbuseReportedUserDTO(
            **build_backoffice_user_dto(users[user_id]).model_dump(),
            photo_file=build_file_dto(storage=storage, file=users[user_id].photo_file),
            parrots=[
                BackofficeParrotDTO(
                    id=parrot.id,
                    name=parrot.name,
                    species=parrot.species,
                    birthdate=parrot.birthdate,
                    photo_file=build_file_dto(storage=storage, file=parrot.photo_file),
                    created_at=parrot.created_at,
                )
                for parrot in parrots
                if parrot.user_id == user_id
            ],
        )
        for user_id in reported_user_ids
    }

    stmt = (
        select(FeedItem)
        .where(FeedItem.id.in_({report.feed_item_id for report in reports if report.feed_item_id is not None}))
        .execution_options(include_deleted=True)
    )
    feed_items = {
        feed_item.id: BackofficeAbuseReportFeedItemDTO(
            id=feed_item.id,
            kind=feed_item.kind,
            word_name=feed_item.word_name,
            file=build_file_dto(storage=storage, file=feed_item.file),
            threshold=feed_item.threshold,
            is_deleted=feed_item.is_deleted,
        )
        for feed_item in (await db.scalars(stmt)).all()
    }

    items = [
        BackofficeAbuseReportDTO(
            id=report.id,
            reporter=build_backoffice_user_dto(users[report.reporter_user_id]),
            reported_user=reported_users[report.reported_user_id],
            feed_item=feed_items.get(report.feed_item_id),
            reason=report.reason,
            description=report.description,
            handled_at=report.handled_at,
            created_at=report.created_at,
        )
        for report in reports
    ]

    return items, total


@transactional(unavailable_error=AbuseReportSaveUnavailableError)
async def handle(*, db: AsyncSession, abuse_report: AbuseReport) -> None:
    if abuse_report.handled_at is None:
        abuse_report.handled_at = datetime.now(UTC)

    await db.flush()

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import LeaderboardPeriodEnum, LeaderboardUnrankedReasonEnum, ScoreMetricEnum
from app.file import build_public_file_dto
from app.models import ScoreEntry, Session, User, UserSetting
from app.r2 import R2StorageClient
from app.schemas.leaderboard import LeaderboardDTO, LeaderboardItemDTO, LeaderboardMeDTO, LeaderboardParams
from app.schemas.users import CommunityUserDTO
from app.services.feed import PUBLIC_USER
from app.services.session_periods import get_active_durations


async def record_finished_sessions(*, db: AsyncSession, sessions: Sequence[Session]) -> None:
    if not sessions:
        return

    durations = await get_active_durations(db=db, sessions=sessions)

    db.add_all(
        [
            ScoreEntry(
                user_id=session.user_id,
                metric=ScoreMetricEnum.LEARNING_TIME,
                amount=durations[session.id],
                occurred_at=session.ended_at,
                session_id=session.id,
            )
            for session in sessions
            if durations[session.id] > 0
        ]
    )


async def get_leaderboard(
    *, db: AsyncSession, storage: R2StorageClient, user: User, query: LeaderboardParams
) -> LeaderboardDTO:
    score_filters = [ScoreEntry.metric == query.metric]

    if query.period == LeaderboardPeriodEnum.MONTHLY:
        month = query.start or datetime.now(UTC).date()
        score_filters += [
            ScoreEntry.occurred_at >= datetime(month.year, month.month, 1, tzinfo=UTC),
            ScoreEntry.occurred_at < datetime(month.year + month.month // 12, month.month % 12 + 1, 1, tzinfo=UTC),
        ]

    score = func.sum(ScoreEntry.amount)

    stmt = (
        select(
            User.id.label("user_id"),
            score.label("score"),
            func.rank().over(order_by=(score.desc(), func.max(ScoreEntry.occurred_at), User.id)).label("rank"),
        )
        .join(ScoreEntry, ScoreEntry.user_id == User.id)
        .outerjoin(UserSetting, UserSetting.user_id == User.id)
        .where(*score_filters, PUBLIC_USER, func.coalesce(UserSetting.leaderboard_enabled, true()))
        .group_by(User.id)
    )

    if query.country is not None:
        stmt = stmt.where(User.country == query.country)

    ranking = stmt.subquery()

    stmt = (
        select(User, ranking.c.score, ranking.c.rank)
        .join(ranking, ranking.c.user_id == User.id)
        .where(or_(ranking.c.rank <= query.limit, User.id == user.id))
        .order_by(ranking.c.rank)
    )
    rows = (await db.execute(stmt)).all()

    my_rank = next((rank for ranked_user, _, rank in rows if ranked_user.id == user.id), None)

    stmt = select(func.coalesce(score, 0)).where(ScoreEntry.user_id == user.id, *score_filters)
    my_score = await db.scalar(stmt)

    setting = await db.get(UserSetting, user.id)
    unranked_reason = None

    if my_rank is None:
        if setting is not None and not setting.leaderboard_enabled:
            unranked_reason = LeaderboardUnrankedReasonEnum.NOT_PARTICIPATING
        elif user.is_anonymous:
            unranked_reason = LeaderboardUnrankedReasonEnum.ANONYMOUS
        elif user.nickname is None:
            unranked_reason = LeaderboardUnrankedReasonEnum.NO_NICKNAME
        elif query.country is not None and user.country != query.country:
            unranked_reason = LeaderboardUnrankedReasonEnum.COUNTRY_MISMATCH
        else:
            unranked_reason = LeaderboardUnrankedReasonEnum.NO_RECORD

    return LeaderboardDTO(
        items=[
            LeaderboardItemDTO(
                rank=rank,
                score=item_score,
                user=CommunityUserDTO(
                    id=ranked_user.id,
                    nickname=ranked_user.nickname,
                    photo_file=build_public_file_dto(storage=storage, file=ranked_user.photo_file),
                    country=ranked_user.country,
                    parrots=[],
                ),
            )
            for ranked_user, item_score, rank in rows
            if rank <= query.limit
        ],
        me=LeaderboardMeDTO(rank=my_rank, unranked_reason=unranked_reason, score=my_score),
    )

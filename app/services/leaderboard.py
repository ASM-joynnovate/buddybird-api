from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import transactional
from app.enums import FeedItemKindEnum, LeaderboardUnrankedReasonEnum, ScoreMetricEnum, SessionStatusEnum
from app.errors import ScoreSaveUnavailableError
from app.models import LearningSegment, ScoreEntry, Session, User, UserSetting, Word
from app.s3 import S3StorageClient
from app.schemas.leaderboard import (
    LeaderboardDTO,
    LeaderboardItemDTO,
    LeaderboardMeDTO,
    LeaderboardParams,
    ScoreBackfillDTO,
)
from app.services.feed import PUBLIC_USER, add_items, build_community_users
from app.services.session_periods import get_active_durations

LEADERBOARD_SIZE = 50
TOTAL_LEARNING_TIME_MILESTONES_MS = [hours * 3_600_000 for hours in (1, 10, 50, 100, 300, 500, 1000)]
MONTHLY_LEARNING_TIME_MILESTONES_MS = [hours * 3_600_000 for hours in (10, 30, 50, 100)]
WORD_PLAY_COUNT_MILESTONES = [100, 500, 1000, 5000, 10000]


async def record_finished_sessions(*, db: AsyncSession, sessions: Sequence[Session], now: datetime) -> None:
    if not sessions:
        return

    durations = await get_active_durations(db=db, sessions=sessions)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    for session in sessions:
        amount = durations[session.id]
        items = []

        if amount > 0:
            stmt = select(
                func.coalesce(func.sum(ScoreEntry.amount), 0),
                func.coalesce(func.sum(ScoreEntry.amount).filter(ScoreEntry.occurred_at >= month_start), 0),
            ).where(ScoreEntry.user_id == session.user_id, ScoreEntry.metric == ScoreMetricEnum.LEARNING_TIME)
            total, monthly = (await db.execute(stmt)).one()

            db.add(
                ScoreEntry(
                    user_id=session.user_id,
                    metric=ScoreMetricEnum.LEARNING_TIME,
                    amount=amount,
                    occurred_at=now,
                    session_id=session.id,
                )
            )

            items += [
                {"kind": FeedItemKindEnum.TOTAL_LEARNING_TIME_REACHED, "threshold": threshold}
                for threshold in TOTAL_LEARNING_TIME_MILESTONES_MS
                if total < threshold <= total + amount
            ]
            items += [
                {"kind": FeedItemKindEnum.MONTHLY_LEARNING_TIME_REACHED, "threshold": threshold}
                for threshold in MONTHLY_LEARNING_TIME_MILESTONES_MS
                if monthly < threshold <= monthly + amount
            ]

        stmt = (
            select(
                LearningSegment.word_id,
                Word.name,
                func.sum(LearningSegment.play_count).filter(LearningSegment.session_id == session.id),
                func.sum(LearningSegment.play_count),
            )
            .join(Word, Word.id == LearningSegment.word_id)
            .where(
                LearningSegment.word_id.in_(
                    select(LearningSegment.word_id).where(LearningSegment.session_id == session.id)
                )
            )
            .group_by(LearningSegment.word_id, Word.name)
            .execution_options(include_deleted=True)
        )

        for word_id, word_name, session_count, total_count in (await db.execute(stmt)).all():
            items += [
                {
                    "kind": FeedItemKindEnum.WORD_PLAY_COUNT_REACHED,
                    "word_id": word_id,
                    "word_name": word_name,
                    "threshold": threshold,
                }
                for threshold in WORD_PLAY_COUNT_MILESTONES
                if total_count - session_count < threshold <= total_count
            ]

        await add_items(db=db, user_id=session.user_id, now=now, items=items)


@transactional(unavailable_error=ScoreSaveUnavailableError)
async def backfill_score_entries(*, db: AsyncSession) -> ScoreBackfillDTO:
    recorded = select(ScoreEntry.id).where(ScoreEntry.session_id == Session.id).exists()
    stmt = select(Session).where(Session.status == SessionStatusEnum.FINISHED, ~recorded)
    sessions = (await db.scalars(stmt)).all()
    durations = await get_active_durations(db=db, sessions=sessions)
    values = [
        {
            "user_id": session.user_id,
            "metric": ScoreMetricEnum.LEARNING_TIME,
            "amount": durations[session.id],
            "occurred_at": session.ended_at,
            "session_id": session.id,
        }
        for session in sessions
        if durations[session.id] > 0
    ]

    if not values:
        return ScoreBackfillDTO(inserted_count=0)

    result = await db.execute(insert(ScoreEntry).values(values).on_conflict_do_nothing())

    return ScoreBackfillDTO(inserted_count=result.rowcount)


async def get_leaderboard(
    *, db: AsyncSession, storage: S3StorageClient, user: User, query: LeaderboardParams
) -> LeaderboardDTO:
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    score = func.sum(ScoreEntry.amount)
    reached_at = func.max(ScoreEntry.occurred_at)

    stmt = (
        select(User.id, score)
        .join(ScoreEntry, ScoreEntry.user_id == User.id)
        .outerjoin(UserSetting, UserSetting.user_id == User.id)
        .where(
            ScoreEntry.metric == query.metric,
            ScoreEntry.occurred_at >= month_start,
            PUBLIC_USER,
            func.coalesce(UserSetting.leaderboard_enabled, true()),
        )
        .group_by(User.id)
        .order_by(score.desc(), reached_at, User.id)
    )

    if query.country is not None:
        stmt = stmt.where(User.country == query.country)

    ranking = (await db.execute(stmt)).all()
    ranks = {user_id: rank for rank, (user_id, _) in enumerate(ranking, start=1)}

    stmt = select(User).where(User.id.in_([user_id for user_id, _ in ranking[:LEADERBOARD_SIZE]]))
    users = await build_community_users(db=db, storage=storage, users=(await db.scalars(stmt)).all())

    stmt = select(func.coalesce(score, 0)).where(
        ScoreEntry.user_id == user.id,
        ScoreEntry.metric == query.metric,
        ScoreEntry.occurred_at >= month_start,
    )
    my_score = await db.scalar(stmt)

    setting = await db.get(UserSetting, user.id)
    unranked_reason = None

    if user.id not in ranks:
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
            LeaderboardItemDTO(rank=rank, score=item_score, user=users[user_id])
            for rank, (user_id, item_score) in enumerate(ranking[:LEADERBOARD_SIZE], start=1)
        ],
        me=LeaderboardMeDTO(rank=ranks.get(user.id), unranked_reason=unranked_reason, score=my_score),
    )

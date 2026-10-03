from datetime import UTC, date, datetime, time, timedelta
from itertools import pairwise
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import ReportPeriodEnum
from app.models import LearningSegment, Session, SessionSound, SoundJudgment, User, Word
from app.schemas.reports import (
    ReportDTO,
    ReportLearningDTO,
    ReportParams,
    ReportPeriodDTO,
    ReportSessionDTO,
    ReportSessionPeriodDTO,
    ReportSessionSoundsDTO,
    ReportSoundsDTO,
    ReportTrendDTO,
    ReportWordDTO,
    ReportWordLearningDTO,
)
from app.schemas.sessions import LearningDurationDTO, SessionJudgmentDTO
from app.services.sessions import get_judgment_statuses


async def get_report(*, db: AsyncSession, user: User, query: ReportParams, timezone: str) -> ReportDTO:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError, ValueError:
        zone = ZoneInfo("UTC")

    if query.period == ReportPeriodEnum.DAY:
        end_date = query.start + timedelta(days=1)
    elif query.period == ReportPeriodEnum.WEEK:
        end_date = query.start + timedelta(days=7)
    else:
        end_date = date(query.start.year + query.start.month // 12, query.start.month % 12 + 1, 1)

    day_starts = [
        datetime.combine(query.start + timedelta(days=day), time(0), tzinfo=zone).astimezone(UTC)
        for day in range((end_date - query.start).days + 1)
    ]
    period_start = day_starts[0]
    period_end = day_starts[-1]

    if query.period == ReportPeriodEnum.DAY:
        boundaries = [period_start]

        while boundaries[-1] < period_end:
            boundaries.append(min(boundaries[-1] + timedelta(hours=1), period_end))
    else:
        boundaries = day_starts

    stmt = (
        select(LearningSegment)
        .join(Session, Session.id == LearningSegment.session_id)
        .where(
            Session.user_id == user.id,
            LearningSegment.started_at < period_end,
            LearningSegment.ended_at > period_start,
        )
    )
    segments = (await db.scalars(stmt)).all()

    stmt = (
        select(Session)
        .where(
            Session.user_id == user.id,
            Session.started_at < period_end,
            func.coalesce(Session.ended_at, datetime.now(UTC)) > period_start,
        )
        .order_by(Session.started_at.desc())
    )
    sessions = (await db.scalars(stmt)).all()

    word_ids = {segment.word_id for segment in segments}

    stmt = (
        select(Word)
        .where(Word.id.in_(word_ids | {session.word_id for session in sessions}))
        .execution_options(include_deleted=True)
    )
    words = {word.id: word for word in (await db.scalars(stmt)).all()}

    latest_word_id = (
        select(SoundJudgment.word_id)
        .where(SoundJudgment.sound_id == SessionSound.id)
        .order_by(SoundJudgment.judged_at.desc())
        .limit(1)
        .scalar_subquery()
    )
    stmt = (
        select(SessionSound)
        .join(Session, Session.id == SessionSound.session_id)
        .where(
            Session.user_id == user.id,
            SessionSound.captured_at >= period_start,
            SessionSound.captured_at < period_end,
        )
    )
    parrot_count = await db.scalar(
        stmt.where(SessionSound.is_parrot_sound.is_(True)).with_only_columns(func.count(), maintain_column_froms=True)
    )
    mimicry_count = await db.scalar(
        stmt.where(latest_word_id.is_not(None)).with_only_columns(func.count(), maintain_column_froms=True)
    )

    stmt = (
        select(SessionSound.session_id, func.count())
        .where(
            SessionSound.session_id.in_([session.id for session in sessions]),
            SessionSound.captured_at >= period_start,
            SessionSound.captured_at < period_end,
            SessionSound.is_parrot_sound.is_(True),
        )
        .group_by(SessionSound.session_id)
    )
    session_parrot_counts = dict((await db.execute(stmt)).all())
    judgment_statuses = await get_judgment_statuses(db=db, sessions=sessions)

    period_durations = {
        segment.id: max(min(segment.ended_at, period_end) - max(segment.started_at, period_start), timedelta(0))
        // timedelta(milliseconds=1)
        for segment in segments
    }
    word_durations = {
        word_id: sum(period_durations[segment.id] for segment in segments if segment.word_id == word_id)
        for word_id in word_ids
    }
    session_durations = {
        session.id: sum(period_durations[segment.id] for segment in segments if segment.session_id == session.id)
        for session in sessions
    }
    trend = [
        ReportTrendDTO(
            start=bucket_start.astimezone(zone),
            duration_ms=sum(
                max(min(segment.ended_at, bucket_end) - max(segment.started_at, bucket_start), timedelta(0))
                // timedelta(milliseconds=1)
                for segment in segments
            ),
        )
        for bucket_start, bucket_end in pairwise(boundaries)
    ]
    words_learning = [
        ReportWordLearningDTO(word=ReportWordDTO(id=word_id, name=words[word_id].name), duration_ms=duration_ms)
        for word_id, duration_ms in sorted(word_durations.items(), key=lambda item: item[1], reverse=True)
    ]

    return ReportDTO(
        period=ReportPeriodDTO(unit=query.period, start=query.start, end=end_date - timedelta(days=1)),
        learning=ReportLearningDTO(duration_ms=sum(period_durations.values()), trend=trend, words=words_learning),
        sounds=ReportSoundsDTO(parrot_count=parrot_count, mimicry_count=mimicry_count),
        sessions=[
            ReportSessionDTO(
                id=session.id,
                period=ReportSessionPeriodDTO(started_at=session.started_at, ended_at=session.ended_at),
                word=ReportWordDTO(id=session.word_id, name=words[session.word_id].name),
                learning=LearningDurationDTO(duration_ms=session_durations[session.id]),
                sounds=ReportSessionSoundsDTO(parrot_count=session_parrot_counts.get(session.id, 0)),
                judgment=SessionJudgmentDTO(status=judgment_statuses[session.id]),
            )
            for session in sessions
        ],
    )

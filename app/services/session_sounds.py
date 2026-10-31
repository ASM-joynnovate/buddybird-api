from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid7

from sqlalchemy import and_, case, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app import sqs
from app.config import config
from app.db import transactional
from app.enums import (
    FeedItemKindEnum,
    FileStatusEnum,
    MimicJudgmentStatusEnum,
    ParrotDetectionStatusEnum,
    SessionEventKindEnum,
    SessionSoundKindEnum,
    SessionSoundLabelTargetEnum,
)
from app.errors import (
    FileSizeExceededError,
    InvalidSessionSoundError,
    SessionSaveUnavailableError,
    SessionSoundNotAnalyzedError,
    SessionSoundNotParrotError,
)
from app.models import (
    Device,
    FeedItem,
    File,
    MimicJudgment,
    ParrotDetection,
    Session,
    SessionEvent,
    SessionEventLabel,
    SessionEventSound,
    SessionEventUserReview,
    SessionSound,
    SessionSoundLabel,
    SessionSoundUserReview,
    User,
    Word,
    WordRecording,
)
from app.s3 import UPLOAD_URL_EXPIRES_IN, S3StorageClient
from app.schemas.base import FileDTO, PageParams, UploadDTO
from app.schemas.sessions import (
    BackofficeMimicJudgmentDTO,
    BackofficeParrotDetectionDTO,
    BackofficeSessionSoundDetailDTO,
    BackofficeSessionSoundDTO,
    BackofficeSessionSoundLabelDTO,
    BackofficeSessionSoundListParams,
    BackofficeSessionSoundUserReviewDTO,
    SessionSoundAnalysisDTO,
    SessionSoundDTO,
    SessionSoundJudgmentDTO,
    SessionSoundListParams,
    SessionSoundUploadRequest,
    SessionUserReviewDTO,
    UpdateSessionUserReviewRequest,
)
from app.services.sessions import verify_station
from app.utils import correctness_filter

MAX_SOUND_BYTES = 5 * 1024 * 1024
SOUND_TYPES = {"audio/wav", "audio/x-wav"}
LATEST_PARROT_LABEL = (
    select(SessionSoundLabel)
    .where(
        SessionSoundLabel.session_sound_id == SessionSound.id,
        SessionSoundLabel.target == SessionSoundLabelTargetEnum.PARROT.value,
    )
    .order_by(SessionSoundLabel.created_at.desc(), SessionSoundLabel.id.desc())
    .limit(1)
)
LATEST_MIMIC_LABEL = (
    select(SessionSoundLabel)
    .where(
        SessionSoundLabel.session_sound_id == SessionSound.id,
        SessionSoundLabel.target == SessionSoundLabelTargetEnum.MIMIC.value,
    )
    .order_by(SessionSoundLabel.created_at.desc(), SessionSoundLabel.id.desc())
    .limit(1)
)
LATEST_PARROT_DETECTION = (
    select(ParrotDetection)
    .where(ParrotDetection.sound_id == SessionSound.id)
    .order_by(ParrotDetection.analyzed_at.desc())
    .limit(1)
)
LATEST_MIMIC_JUDGMENT = (
    select(MimicJudgment)
    .where(MimicJudgment.sound_id == SessionSound.id)
    .order_by(MimicJudgment.judged_at.desc())
    .limit(1)
)
IS_PARROT = func.coalesce(
    LATEST_PARROT_LABEL.with_only_columns(SessionSoundLabel.is_positive).scalar_subquery(),
    LATEST_PARROT_DETECTION.with_only_columns(ParrotDetection.is_parrot).scalar_subquery(),
)
IS_MIMIC = func.coalesce(
    LATEST_MIMIC_LABEL.with_only_columns(SessionSoundLabel.is_positive).scalar_subquery(),
    LATEST_MIMIC_JUDGMENT.with_only_columns(MimicJudgment.word_id.is_not(None)).scalar_subquery(),
)
FINAL_RESULT = {
    "kind": case(
        (and_(IS_PARROT.is_(True), IS_MIMIC.is_(True)), SessionSoundKindEnum.MIMIC.value),
        (IS_PARROT.is_(True), SessionSoundKindEnum.PARROT.value),
        (IS_PARROT.is_(False), SessionSoundKindEnum.NOT_PARROT.value),
    ),
    "final_parrot_score": func.coalesce(
        LATEST_PARROT_LABEL.with_only_columns(SessionSoundLabel.score).scalar_subquery(),
        LATEST_PARROT_DETECTION.with_only_columns(ParrotDetection.score).scalar_subquery(),
    ),
    "final_mimic_score": func.coalesce(
        LATEST_MIMIC_LABEL.with_only_columns(SessionSoundLabel.score).scalar_subquery(),
        LATEST_MIMIC_JUDGMENT.with_only_columns(MimicJudgment.score).scalar_subquery(),
    ),
}
IS_LABELED = or_(
    LATEST_PARROT_LABEL.with_only_columns(SessionSoundLabel.is_positive).scalar_subquery().is_not(None),
    LATEST_MIMIC_LABEL.with_only_columns(SessionSoundLabel.is_positive).scalar_subquery().is_not(None),
)


async def build_sound_dtos(
    *, db: AsyncSession, storage: S3StorageClient, sounds: Sequence[SessionSound]
) -> list[SessionSoundDTO]:
    stmt = select(Session.id, Session.word_id).where(Session.id.in_({sound.session_id for sound in sounds}))
    session_word_ids = dict((await db.execute(stmt)).all())

    stmt = select(SessionSoundUserReview).where(
        SessionSoundUserReview.session_sound_id.in_([sound.id for sound in sounds])
    )
    reviews = {review.session_sound_id: review for review in (await db.scalars(stmt)).all()}

    stmt = (
        select(FeedItem.file_id)
        .where(
            FeedItem.kind == FeedItemKindEnum.MIMIC_SUCCEEDED.value,
            FeedItem.file_id.in_([sound.audio_file_id for sound in sounds]),
        )
        .execution_options(include_deleted=True)
    )
    shared_file_ids = set((await db.scalars(stmt)).all())

    return [
        SessionSoundDTO(
            id=sound.id,
            session_id=sound.session_id,
            captured_at=sound.captured_at,
            audio_file=FileDTO(
                url=storage.generate_presigned_url(path=sound.audio_file.object_key),
                status=sound.audio_file.status,
            ),
            duration_ms=sound.duration_ms,
            analysis=SessionSoundAnalysisDTO(score=sound.final_parrot_score)
            if sound.final_parrot_score is not None
            else None,
            judgment=SessionSoundJudgmentDTO(
                word_id=session_word_ids[sound.session_id] if sound.kind == SessionSoundKindEnum.MIMIC else None,
                score=sound.final_mimic_score,
            )
            if sound.final_mimic_score is not None
            else None,
            user_review=SessionUserReviewDTO(is_correct=reviews[sound.id].is_correct)
            if sound.id in reviews and reviews[sound.id].kind == sound.kind
            else None,
            is_feed_shared=sound.audio_file_id in shared_file_ids,
        )
        for sound in sounds
    ]


async def get_list(
    *, db: AsyncSession, storage: S3StorageClient, session: Session, query: SessionSoundListParams
) -> tuple[list[SessionSoundDTO], int]:
    stmt = (
        select(SessionSound)
        .join(File, File.id == SessionSound.audio_file_id)
        .where(
            SessionSound.session_id == session.id,
            SessionSound.kind.is_distinct_from(SessionSoundKindEnum.NOT_PARROT.value),
            SessionSound.parrot_detection_status != ParrotDetectionStatusEnum.FAILED.value,
            or_(
                File.status == FileStatusEnum.UPLOADED.value,
                and_(
                    File.status == FileStatusEnum.PENDING.value,
                    File.created_at > datetime.now(UTC) - timedelta(seconds=UPLOAD_URL_EXPIRES_IN),
                ),
            ),
        )
    )

    if query.mimic:
        stmt = stmt.where(SessionSound.kind == SessionSoundKindEnum.MIMIC.value)

    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    sounds = (
        await db.scalars(
            stmt.options(contains_eager(SessionSound.audio_file))
            .order_by(SessionSound.captured_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return await build_sound_dtos(db=db, storage=storage, sounds=sounds), total


async def get_user_list(
    *, db: AsyncSession, storage: S3StorageClient, user: User, query: PageParams
) -> tuple[list[SessionSoundDTO], int]:
    stmt = (
        select(SessionSound)
        .join(Session, Session.id == SessionSound.session_id)
        .join(File, File.id == SessionSound.audio_file_id)
        .where(
            Session.user_id == user.id,
            SessionSound.kind.is_distinct_from(SessionSoundKindEnum.NOT_PARROT.value),
            SessionSound.parrot_detection_status != ParrotDetectionStatusEnum.FAILED.value,
            File.status == FileStatusEnum.UPLOADED.value,
        )
    )
    total = await db.scalar(stmt.with_only_columns(func.count(), maintain_column_froms=True))
    sounds = (
        await db.scalars(
            stmt.options(contains_eager(SessionSound.audio_file))
            .order_by(SessionSound.captured_at.desc())
            .offset((query.page - 1) * query.count_by_page)
            .limit(query.count_by_page)
        )
    ).all()

    return await build_sound_dtos(db=db, storage=storage, sounds=sounds), total


async def get_backoffice_list(
    *, db: AsyncSession, storage: S3StorageClient, session: Session, query: BackofficeSessionSoundListParams
) -> list[BackofficeSessionSoundDTO]:
    stmt = select(SessionSound).where(SessionSound.session_id == session.id).order_by(SessionSound.captured_at)

    if query.kind is not None:
        stmt = stmt.where(SessionSound.kind.in_(query.kind))

    if query.user_review is not None:
        review = (
            select(SessionSoundUserReview.is_correct)
            .where(SessionSoundUserReview.session_sound_id == SessionSound.id)
            .scalar_subquery()
        )
        stmt = stmt.where(correctness_filter(review, query.user_review))

    sounds = (await db.scalars(stmt)).all()

    stmt = select(SessionSound.id, IS_LABELED).where(SessionSound.id.in_([sound.id for sound in sounds]))
    labeled = dict((await db.execute(stmt)).all())

    stmt = select(SessionSoundUserReview).where(
        SessionSoundUserReview.session_sound_id.in_([sound.id for sound in sounds])
    )
    reviews = {review.session_sound_id: review for review in (await db.scalars(stmt)).all()}

    return [
        BackofficeSessionSoundDTO(
            **dto.model_dump(exclude={"user_review"}),
            user_review=BackofficeSessionSoundUserReviewDTO(
                is_correct=reviews[sound.id].is_correct,
                kind=reviews[sound.id].kind,
                updated_at=reviews[sound.id].updated_at,
            )
            if sound.id in reviews
            else None,
            kind=sound.kind,
            final_parrot_score=sound.final_parrot_score,
            final_mimic_score=sound.final_mimic_score,
            is_labeled=labeled[sound.id],
        )
        for sound, dto in zip(sounds, await build_sound_dtos(db=db, storage=storage, sounds=sounds), strict=True)
    ]


async def get_backoffice_detail(
    *, db: AsyncSession, storage: S3StorageClient, sound: SessionSound
) -> BackofficeSessionSoundDetailDTO:
    [dto] = await build_sound_dtos(db=db, storage=storage, sounds=[sound])

    stmt = select(IS_LABELED).where(SessionSound.id == sound.id)
    is_labeled = await db.scalar(stmt)

    stmt = select(SessionSoundUserReview).where(SessionSoundUserReview.session_sound_id == sound.id)
    review = await db.scalar(stmt)

    stmt = select(ParrotDetection).where(ParrotDetection.sound_id == sound.id).order_by(ParrotDetection.analyzed_at)
    detections = (await db.scalars(stmt)).all()

    stmt = select(MimicJudgment).where(MimicJudgment.sound_id == sound.id).order_by(MimicJudgment.judged_at)
    judgments = (await db.scalars(stmt)).all()

    stmt = (
        select(SessionSoundLabel)
        .where(SessionSoundLabel.session_sound_id == sound.id)
        .order_by(SessionSoundLabel.created_at, SessionSoundLabel.id)
    )
    labels = (await db.scalars(stmt)).all()

    return BackofficeSessionSoundDetailDTO(
        **dto.model_dump(exclude={"user_review"}),
        user_review=BackofficeSessionSoundUserReviewDTO(
            is_correct=review.is_correct,
            kind=review.kind,
            updated_at=review.updated_at,
        )
        if review is not None
        else None,
        kind=sound.kind,
        final_parrot_score=sound.final_parrot_score,
        final_mimic_score=sound.final_mimic_score,
        is_labeled=is_labeled,
        parrot_detections=[
            BackofficeParrotDetectionDTO(
                model_version=detection.model_version,
                is_parrot=detection.is_parrot,
                score=detection.score,
                call_count=detection.call_count,
                chirp_count=detection.chirp_count,
                analyzed_at=detection.analyzed_at,
            )
            for detection in detections
        ],
        mimic_judgments=[
            BackofficeMimicJudgmentDTO(
                model_version=judgment.model_version,
                word_id=judgment.word_id,
                score=judgment.score,
                judged_at=judgment.judged_at,
            )
            for judgment in judgments
        ],
        labels=[
            BackofficeSessionSoundLabelDTO(
                id=label.id,
                target=label.target,
                is_positive=label.is_positive,
                score=label.score,
                operator_name=label.operator_name,
                memo=label.memo,
                created_at=label.created_at,
            )
            for label in labels
        ],
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def update_user_review(*, db: AsyncSession, sound: SessionSound, data: UpdateSessionUserReviewRequest) -> None:
    if sound.kind is None:
        raise SessionSoundNotAnalyzedError

    if sound.kind == SessionSoundKindEnum.NOT_PARROT:
        raise SessionSoundNotParrotError

    stmt = insert(SessionSoundUserReview).values(session_sound_id=sound.id, is_correct=data.is_correct, kind=sound.kind)

    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=[SessionSoundUserReview.session_sound_id],
            set_={"is_correct": stmt.excluded.is_correct, "kind": stmt.excluded.kind, "updated_at": func.now()},
        )
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def delete_user_review(*, db: AsyncSession, sound: SessionSound) -> None:
    await db.execute(delete(SessionSoundUserReview).where(SessionSoundUserReview.session_sound_id == sound.id))


@transactional(unavailable_error=SessionSaveUnavailableError)
async def add_label(
    *,
    db: AsyncSession,
    sound: SessionSound,
    target: SessionSoundLabelTargetEnum,
    is_positive: bool | None,
    score: float | None,
    memo: str | None,
    operator_name: str,
) -> None:
    db.add(
        SessionSoundLabel(
            session_sound_id=sound.id,
            target=target.value,
            is_positive=is_positive,
            score=score,
            operator_name=operator_name,
            memo=memo,
        )
    )

    await db.flush()

    await db.execute(update(SessionSound).where(SessionSound.id == sound.id).values(**FINAL_RESULT))


async def request_mimic_judgment(*, db: AsyncSession, sound_id: UUID, session_id: UUID, audio_file_id: UUID) -> None:
    await db.execute(
        update(SessionSound)
        .where(SessionSound.id == sound_id)
        .values(mimic_judgment_status=MimicJudgmentStatusEnum.PENDING.value)
    )

    stmt = select(File).where(File.id == audio_file_id).execution_options(include_deleted=True)
    audio_file = await db.scalar(stmt)

    stmt = (
        select(Word)
        .join(Session, Session.word_id == Word.id)
        .where(Session.id == session_id)
        .execution_options(include_deleted=True)
    )
    word = await db.scalar(stmt)

    stmt = (
        select(File)
        .join(WordRecording, WordRecording.file_id == File.id)
        .where(WordRecording.word_id == word.id, File.status == FileStatusEnum.UPLOADED.value)
        .order_by(WordRecording.display_order, WordRecording.created_at)
    )
    recording_files = (await db.scalars(stmt)).all()

    await sqs.send(
        queue_url=config.SQS_MIMICRY_JUDGMENT_QUEUE_URL,
        body={
            "type": "audio.judge_mimic",
            "session_id": str(session_id),
            "target": {"audio_id": str(sound_id), "object_key": audio_file.object_key},
            "reference": {
                "word_id": str(word.id),
                "word_name": word.name,
                "object_keys": [file.object_key for file in recording_files],
            },
        },
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def request_backoffice_mimic_judgment(*, db: AsyncSession, sound: SessionSound) -> None:
    if sound.kind is None:
        raise SessionSoundNotAnalyzedError

    if sound.kind == SessionSoundKindEnum.NOT_PARROT:
        raise SessionSoundNotParrotError

    await request_mimic_judgment(
        db=db,
        sound_id=sound.id,
        session_id=sound.session_id,
        audio_file_id=sound.audio_file_id,
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def upload(
    *,
    db: AsyncSession,
    storage: S3StorageClient,
    session: Session,
    device: Device,
    data: SessionSoundUploadRequest,
) -> UploadDTO:
    verify_station(session, device)

    if data.content_type not in SOUND_TYPES:
        raise InvalidSessionSoundError

    if data.file_size > MAX_SOUND_BYTES:
        raise FileSizeExceededError

    file_id = uuid7()
    file_path = f"user/{session.user_id}/session/{session.id}/sound/{file_id}"

    audio_file = File(
        id=file_id,
        file_name="sound.wav",
        file_path=file_path,
        file_size=data.file_size,
        file_type=data.content_type,
        is_deleted=False,
        status=FileStatusEnum.PENDING.value,
    )

    db.add(audio_file)
    db.add(
        SessionSound(
            session_id=session.id,
            captured_at=data.captured_at,
            audio_file=audio_file,
            is_deleted=False,
        )
    )

    await db.flush()

    return storage.generate_presigned_upload(
        file_id=file_id,
        path=audio_file.object_key,
        content_type=data.content_type,
        file_size=data.file_size,
    )


async def detect_emergency(*, db: AsyncSession, session_id: UUID, captured_at: datetime) -> None:
    window_size = timedelta(seconds=30)
    latest_chirp_count = (
        select(ParrotDetection.chirp_count)
        .where(ParrotDetection.sound_id == SessionSound.id)
        .order_by(ParrotDetection.analyzed_at.desc())
        .limit(1)
        .scalar_subquery()
    )
    stmt = (
        select(SessionSound.id, SessionSound.captured_at, func.coalesce(latest_chirp_count, 0).label("chirp_count"))
        .join(File, File.id == SessionSound.audio_file_id)
        .where(
            SessionSound.session_id == session_id,
            SessionSound.captured_at.between(captured_at - window_size, captured_at + window_size),
            File.status == FileStatusEnum.UPLOADED.value,
        )
        .order_by(SessionSound.captured_at)
    )
    sounds = (await db.execute(stmt)).all()

    windows = [
        [sound for sound in sounds if end.captured_at - window_size <= sound.captured_at <= end.captured_at]
        for end in sounds
        if end.captured_at >= captured_at
    ]
    emergencies = [window for window in windows if sum(sound.chirp_count for sound in window) >= 7]

    if not emergencies:
        return

    started_at = emergencies[0][0].captured_at
    ended_at = emergencies[-1][-1].captured_at
    sound_ids = {sound.id for sound in sounds if started_at <= sound.captured_at <= ended_at}

    stmt = (
        select(SessionEvent)
        .join(SessionEventSound, SessionEventSound.event_id == SessionEvent.id)
        .join(SessionSound, SessionSound.id == SessionEventSound.sound_id)
        .where(
            SessionEvent.session_id == session_id,
            SessionEvent.kind == SessionEventKindEnum.DISTRESS_CALL_DETECTED.value,
            SessionEvent.occurred_at <= ended_at,
            SessionSound.captured_at >= started_at,
        )
        .distinct()
        .order_by(SessionEvent.occurred_at)
    )
    events = (await db.scalars(stmt)).all()

    if events:
        event = events[0]

        event.occurred_at = min(event.occurred_at, started_at)
    else:
        event = SessionEvent(
            session_id=session_id,
            kind=SessionEventKindEnum.DISTRESS_CALL_DETECTED.value,
            occurred_at=started_at,
        )

        db.add(event)

        await db.flush()

    for merged in events[1:]:
        stmt = select(SessionEventSound.sound_id).where(SessionEventSound.event_id == merged.id)
        sound_ids.update((await db.scalars(stmt)).all())

        await db.execute(delete(SessionEventSound).where(SessionEventSound.event_id == merged.id))

        stmt = select(SessionEventUserReview.session_event_id).where(
            SessionEventUserReview.session_event_id == event.id
        )

        if await db.scalar(stmt) is None:
            await db.execute(
                update(SessionEventUserReview)
                .where(SessionEventUserReview.session_event_id == merged.id)
                .values(session_event_id=event.id)
            )
        else:
            await db.execute(delete(SessionEventUserReview).where(SessionEventUserReview.session_event_id == merged.id))

        await db.execute(
            update(SessionEventLabel)
            .where(SessionEventLabel.session_event_id == merged.id)
            .values(session_event_id=event.id)
        )

        stmt = (
            select(SessionEventLabel.is_correct)
            .where(SessionEventLabel.session_event_id == event.id)
            .order_by(SessionEventLabel.created_at.desc(), SessionEventLabel.id.desc())
            .limit(1)
        )
        event.is_correct = await db.scalar(stmt)

        await db.delete(merged)

    await db.execute(
        insert(SessionEventSound)
        .values([{"event_id": event.id, "sound_id": sound_id} for sound_id in sound_ids])
        .on_conflict_do_nothing()
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def save_parrot_detection(
    *, db: AsyncSession, model_version: str, analyzed_at: datetime, data: list[dict]
) -> list[UUID]:
    session_ids = set()

    for item in data:
        sound_id = UUID(item["audio_id"])

        stmt = (
            select(Session.id)
            .join(SessionSound, SessionSound.session_id == Session.id)
            .where(SessionSound.id == sound_id)
            .with_for_update(of=Session, key_share=True)
        )
        await db.execute(stmt)

        await db.execute(
            insert(ParrotDetection)
            .values(
                sound_id=sound_id,
                model_version=model_version,
                is_parrot=item["is_parrot"],
                score=item["score"],
                call_count=item["call_count"],
                chirp_count=item["chirp_count"],
                analyzed_at=analyzed_at,
            )
            .on_conflict_do_nothing(index_elements=[ParrotDetection.sound_id, ParrotDetection.model_version])
        )

        sound = (
            await db.execute(
                update(SessionSound)
                .where(SessionSound.id == sound_id)
                .values(**FINAL_RESULT, parrot_detection_status=ParrotDetectionStatusEnum.DONE.value)
                .returning(
                    SessionSound.session_id,
                    SessionSound.captured_at,
                    SessionSound.audio_file_id,
                    SessionSound.kind,
                )
            )
        ).one()

        await detect_emergency(db=db, session_id=sound.session_id, captured_at=sound.captured_at)

        session_ids.add(sound.session_id)

        if sound.kind == SessionSoundKindEnum.NOT_PARROT:
            continue

        await request_mimic_judgment(
            db=db,
            sound_id=sound_id,
            session_id=sound.session_id,
            audio_file_id=sound.audio_file_id,
        )

    return list(session_ids)


@transactional(unavailable_error=SessionSaveUnavailableError)
async def mark_parrot_detection_failed(*, db: AsyncSession, data: list[dict]) -> None:
    await db.execute(
        update(SessionSound)
        .where(
            SessionSound.id.in_([UUID(item["audio_id"]) for item in data]),
            SessionSound.parrot_detection_status == ParrotDetectionStatusEnum.PENDING.value,
        )
        .values(parrot_detection_status=ParrotDetectionStatusEnum.FAILED.value)
    )


@transactional(unavailable_error=SessionSaveUnavailableError)
async def save_mimic_judgment(
    *, db: AsyncSession, sound_id: UUID, word_id: UUID, model_version: str, judged_at: datetime, judgment: dict
) -> None:
    await db.execute(
        update(SessionSound)
        .where(SessionSound.id == sound_id)
        .values(mimic_judgment_status=MimicJudgmentStatusEnum.DONE.value)
    )

    if judgment["status"] == "no_reference":
        return

    db.add(
        MimicJudgment(
            sound_id=sound_id,
            word_id=word_id if judgment["is_success"] else None,
            score=judgment["score"],
            model_version=model_version,
            judged_at=judged_at,
        )
    )

    await db.flush()

    await db.execute(update(SessionSound).where(SessionSound.id == sound_id).values(**FINAL_RESULT))


@transactional(unavailable_error=SessionSaveUnavailableError)
async def mark_mimic_judgment_failed(*, db: AsyncSession, sound_id: UUID) -> None:
    await db.execute(
        update(SessionSound)
        .where(
            SessionSound.id == sound_id,
            SessionSound.mimic_judgment_status == MimicJudgmentStatusEnum.PENDING.value,
        )
        .values(mimic_judgment_status=MimicJudgmentStatusEnum.FAILED.value)
    )

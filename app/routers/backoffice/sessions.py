from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import (
    DBSession,
    Storage,
    require_backoffice_session,
    require_backoffice_session_event,
    require_backoffice_session_sound,
)
from app.enums import SessionSoundLabelTargetEnum
from app.models import Session, SessionEvent, SessionSound
from app.schemas.base import BaseResponse
from app.schemas.sessions import (
    BackofficeSessionEventDetailResponse,
    BackofficeSessionEventListParams,
    BackofficeSessionEventListResponse,
    BackofficeSessionSoundDetailResponse,
    BackofficeSessionSoundListParams,
    BackofficeSessionSoundListResponse,
    CancelSessionLabelRequest,
    UpdateSessionEventLabelRequest,
    UpdateSessionSoundLabelRequest,
)
from app.services import session_sounds, sessions

router = APIRouter(prefix="/sessions")


@router.get("/{session_id}/events", name="세션 이벤트 조회")
async def get_events(
    session: Annotated[Session, Depends(require_backoffice_session)],
    query: Annotated[BackofficeSessionEventListParams, Query()],
    db: DBSession,
    storage: Storage,
) -> BackofficeSessionEventListResponse:
    return BackofficeSessionEventListResponse(
        message="세션 이벤트 조회 성공",
        data=await sessions.get_backoffice_events(db=db, storage=storage, session=session, query=query),
    )


@router.get("/{session_id}/events/{session_event_id}", name="세션 이벤트 상세 조회")
async def get_event(
    event: Annotated[SessionEvent, Depends(require_backoffice_session_event)], db: DBSession
) -> BackofficeSessionEventDetailResponse:
    return BackofficeSessionEventDetailResponse(
        message="세션 이벤트 상세 조회 성공",
        data=await sessions.get_backoffice_event(db=db, event=event),
    )


@router.put("/{session_id}/events/{session_event_id}/label", name="세션 이벤트 라벨 저장")
async def label_event(
    session: Annotated[Session, Depends(require_backoffice_session)],
    event: Annotated[SessionEvent, Depends(require_backoffice_session_event)],
    body: UpdateSessionEventLabelRequest,
    db: DBSession,
) -> BaseResponse:
    await sessions.add_event_label(
        db=db,
        session=session,
        event=event,
        is_correct=body.is_correct,
        memo=body.memo,
        operator_name=body.operator_name,
    )

    return BaseResponse(message="세션 이벤트 라벨 저장 성공")


@router.post("/{session_id}/events/{session_event_id}/label/cancel", name="세션 이벤트 라벨 취소")
async def cancel_event_label(
    session: Annotated[Session, Depends(require_backoffice_session)],
    event: Annotated[SessionEvent, Depends(require_backoffice_session_event)],
    body: CancelSessionLabelRequest,
    db: DBSession,
) -> BaseResponse:
    await sessions.add_event_label(
        db=db,
        session=session,
        event=event,
        is_correct=None,
        memo=body.memo,
        operator_name=body.operator_name,
    )

    return BaseResponse(message="세션 이벤트 라벨 취소 성공")


@router.get("/{session_id}/sounds", name="세션 소리 시각 조회")
async def get_sounds(
    session: Annotated[Session, Depends(require_backoffice_session)],
    query: Annotated[BackofficeSessionSoundListParams, Query()],
    db: DBSession,
    storage: Storage,
) -> BackofficeSessionSoundListResponse:
    return BackofficeSessionSoundListResponse(
        message="세션 소리 시각 조회 성공",
        data=await session_sounds.get_backoffice_list(db=db, storage=storage, session=session, query=query),
    )


@router.get("/{session_id}/sounds/{session_sound_id}", name="세션 소리 상세 조회")
async def get_sound(
    sound: Annotated[SessionSound, Depends(require_backoffice_session_sound)], db: DBSession, storage: Storage
) -> BackofficeSessionSoundDetailResponse:
    return BackofficeSessionSoundDetailResponse(
        message="세션 소리 상세 조회 성공",
        data=await session_sounds.get_backoffice_detail(db=db, storage=storage, sound=sound),
    )


@router.put("/{session_id}/sounds/{session_sound_id}/labels/{target}", name="세션 소리 라벨 저장")
async def label_sound(
    sound: Annotated[SessionSound, Depends(require_backoffice_session_sound)],
    target: SessionSoundLabelTargetEnum,
    body: UpdateSessionSoundLabelRequest,
    db: DBSession,
) -> BaseResponse:
    await session_sounds.add_label(
        db=db,
        sound=sound,
        target=target,
        is_positive=body.is_positive,
        score=body.score,
        memo=body.memo,
        operator_name=body.operator_name,
    )

    return BaseResponse(message="세션 소리 라벨 저장 성공")


@router.post("/{session_id}/sounds/{session_sound_id}/labels/{target}/cancel", name="세션 소리 라벨 취소")
async def cancel_sound_label(
    sound: Annotated[SessionSound, Depends(require_backoffice_session_sound)],
    target: SessionSoundLabelTargetEnum,
    body: CancelSessionLabelRequest,
    db: DBSession,
) -> BaseResponse:
    await session_sounds.add_label(
        db=db,
        sound=sound,
        target=target,
        is_positive=None,
        score=None,
        memo=body.memo,
        operator_name=body.operator_name,
    )

    return BaseResponse(message="세션 소리 라벨 취소 성공")


@router.post("/{session_id}/sounds/{session_sound_id}/mimic-judgments", name="세션 소리 모사 판정 요청")
async def request_mimic_judgment(
    sound: Annotated[SessionSound, Depends(require_backoffice_session_sound)], db: DBSession
) -> BaseResponse:
    await session_sounds.request_backoffice_mimic_judgment(db=db, sound=sound)

    return BaseResponse(message="세션 소리 모사 판정 요청 성공")

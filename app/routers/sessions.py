from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import ActiveDevice, ActiveUser, DBSession, Storage, require_session
from app.models import Session
from app.schemas.base import BaseResponse, PageParams, UploadResponse
from app.schemas.sessions import (
    AddSessionEventsRequest,
    ChangeSessionLearningRequest,
    ChangeSessionWordRequest,
    HeartbeatRequest,
    HeartbeatResponse,
    SessionEventListResponse,
    SessionListResponse,
    SessionResponse,
    SessionSoundListResponse,
    SessionSoundUploadRequest,
    StartSessionRequest,
)
from app.services import session_sounds, sessions

router = APIRouter(prefix="/sessions")


@router.post("", name="세션 시작", response_model=SessionResponse)
async def start(user: ActiveUser, device: ActiveDevice, body: StartSessionRequest, db: DBSession) -> SessionResponse:
    return SessionResponse(
        message="세션 시작 성공", data=await sessions.start(db=db, user=user, device=device, data=body)
    )


@router.get("", name="세션 목록 조회", response_model=SessionListResponse)
async def get_list(user: ActiveUser, query: Annotated[PageParams, Query()], db: DBSession) -> SessionListResponse:
    items, total = await sessions.get_list(db=db, user=user, query=query)

    return SessionListResponse(
        message="세션 목록 조회 성공",
        data=items,
        meta={
            "current_page": query.page,
            "total_page_count": (total + query.count_by_page - 1) // query.count_by_page,
            "is_first": query.page == 1,
            "is_last": query.page * query.count_by_page >= total,
        },
    )


@router.get("/{session_id}", name="세션 상세 조회", response_model=SessionResponse)
async def get_detail(session: Annotated[Session, Depends(require_session)]) -> SessionResponse:
    return SessionResponse(message="세션 상세 조회 성공", data=sessions.get_detail(session=session))


@router.put("/{session_id}/word", name="세션 학습 단어 변경", response_model=SessionResponse)
async def change_word(
    session: Annotated[Session, Depends(require_session)],
    device: ActiveDevice,
    body: ChangeSessionWordRequest,
    db: DBSession,
) -> SessionResponse:
    return SessionResponse(
        message="세션 학습 단어 변경 성공",
        data=await sessions.change_word(db=db, session=session, device=device, data=body),
    )


@router.put("/{session_id}/learning", name="세션 학습 켜기 끄기", response_model=SessionResponse)
async def change_learning(
    session: Annotated[Session, Depends(require_session)],
    device: ActiveDevice,
    body: ChangeSessionLearningRequest,
    db: DBSession,
) -> SessionResponse:
    return SessionResponse(
        message="세션 학습 설정 변경 성공",
        data=await sessions.change_learning(db=db, session=session, device=device, data=body),
    )


@router.post("/{session_id}/finish", name="세션 종료", response_model=SessionResponse)
async def finish(
    session: Annotated[Session, Depends(require_session)], device: ActiveDevice, db: DBSession
) -> SessionResponse:
    return SessionResponse(message="세션 종료 성공", data=await sessions.finish(db=db, session=session, device=device))


@router.post("/{session_id}/heartbeat", name="세션 heartbeat", response_model=HeartbeatResponse)
async def record_heartbeat(
    session: Annotated[Session, Depends(require_session)], device: ActiveDevice, body: HeartbeatRequest, db: DBSession
) -> HeartbeatResponse:
    return HeartbeatResponse(
        message="heartbeat 성공",
        data=await sessions.record_heartbeat(db=db, session=session, device=device, data=body),
    )


@router.post("/{session_id}/events", name="세션 이벤트 기록")
async def add_events(
    session: Annotated[Session, Depends(require_session)],
    device: ActiveDevice,
    body: AddSessionEventsRequest,
    db: DBSession,
) -> BaseResponse:
    await sessions.add_events(db=db, session=session, device=device, data=body)

    return BaseResponse(message="세션 이벤트 기록 성공")


@router.get("/{session_id}/events", name="세션 이벤트 조회", response_model=SessionEventListResponse)
async def get_events(session: Annotated[Session, Depends(require_session)], db: DBSession) -> SessionEventListResponse:
    return SessionEventListResponse(
        message="세션 이벤트 조회 성공", data=await sessions.get_events(db=db, session=session)
    )


@router.post("/{session_id}/sounds", name="세션 소리 업로드 URL 발급", response_model=UploadResponse)
async def upload_sound(
    session: Annotated[Session, Depends(require_session)],
    device: ActiveDevice,
    body: SessionSoundUploadRequest,
    db: DBSession,
    storage: Storage,
) -> UploadResponse:
    return UploadResponse(
        message="세션 소리 업로드 URL 발급 성공",
        data=await session_sounds.upload(db=db, storage=storage, session=session, device=device, data=body),
    )


@router.get("/{session_id}/sounds", name="세션 소리 목록 조회", response_model=SessionSoundListResponse)
async def get_sounds(
    session: Annotated[Session, Depends(require_session)],
    query: Annotated[PageParams, Query()],
    db: DBSession,
    storage: Storage,
) -> SessionSoundListResponse:
    items, total = await session_sounds.get_list(db=db, storage=storage, session=session, query=query)

    return SessionSoundListResponse(
        message="세션 소리 목록 조회 성공",
        data=items,
        meta={
            "current_page": query.page,
            "total_page_count": (total + query.count_by_page - 1) // query.count_by_page,
            "is_first": query.page == 1,
            "is_last": query.page * query.count_by_page >= total,
        },
    )

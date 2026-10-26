from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import (
    ActiveDevice,
    ActiveUser,
    Country,
    DBSession,
    Storage,
    require_device,
    require_session,
    require_session_event,
    require_session_sound,
)
from app.models import Session, SessionEvent, SessionSound
from app.schemas.base import BaseResponse, PageParams, UploadResponse
from app.schemas.sessions import (
    AddSessionEventsRequest,
    HeartbeatRequest,
    HeartbeatResponse,
    SessionEventListParams,
    SessionEventListResponse,
    SessionListResponse,
    SessionPetcamEventRequest,
    SessionPetcamEventUploadResponse,
    SessionPetcamVideoUploadRequest,
    SessionResponse,
    SessionSoundListParams,
    SessionSoundListResponse,
    SessionSoundUploadRequest,
    SessionSummaryResponse,
    StartSessionRequest,
    UpdateSessionUserReviewRequest,
)
from app.services import notifications, session_sounds, sessions

router = APIRouter(prefix="/sessions")


@router.post("", name="세션 시작")
async def start(user: ActiveUser, device: ActiveDevice, body: StartSessionRequest, db: DBSession) -> SessionResponse:
    return SessionResponse(
        message="세션 시작 성공", data=await sessions.start(db=db, user=user, device=device, data=body)
    )


@router.get("", name="세션 목록 조회")
async def get_list(user: ActiveUser, query: Annotated[PageParams, Query()], db: DBSession) -> SessionListResponse:
    items, total = await sessions.get_list(db=db, user=user, query=query)

    return SessionListResponse(
        message="세션 목록 조회 성공",
        data=items,
        meta=query.meta(total),
    )


@router.get("/{session_id}", name="세션 상세 조회")
async def get_detail(session: Annotated[Session, Depends(require_session)], db: DBSession) -> SessionResponse:
    return SessionResponse(message="세션 상세 조회 성공", data=await sessions.get_detail(db=db, session=session))


@router.post(
    "/{session_id}/finish",
    name="세션 종료",
    dependencies=[Depends(require_device)],
)
async def finish(session: Annotated[Session, Depends(require_session)], db: DBSession) -> SessionResponse:
    data = await sessions.finish(db=db, session=session)

    await notifications.send_report(db=db, session_ids=[session.id])

    return SessionResponse(message="세션 종료 성공", data=data)


@router.post("/{session_id}/heartbeat", name="세션 heartbeat")
async def record_heartbeat(
    session: Annotated[Session, Depends(require_session)],
    device: ActiveDevice,
    body: HeartbeatRequest,
    country: Country,
    db: DBSession,
) -> HeartbeatResponse:
    return HeartbeatResponse(
        message="heartbeat 성공",
        data=await sessions.record_heartbeat(db=db, session=session, device=device, data=body, country=country),
    )


@router.post("/{session_id}/events", name="세션 이벤트 기록", dependencies=[Depends(require_device)])
async def add_events(
    session: Annotated[Session, Depends(require_session)],
    body: AddSessionEventsRequest,
    db: DBSession,
) -> BaseResponse:
    await sessions.add_events(db=db, session=session, data=body)

    return BaseResponse(message="세션 이벤트 기록 성공")


@router.get("/{session_id}/events", name="세션 이벤트 조회")
async def get_events(
    session: Annotated[Session, Depends(require_session)],
    query: Annotated[SessionEventListParams, Query()],
    db: DBSession,
    storage: Storage,
) -> SessionEventListResponse:
    return SessionEventListResponse(
        message="세션 이벤트 조회 성공",
        data=await sessions.get_events(
            db=db,
            storage=storage,
            session=session,
            petcam=query.petcam,
            distress_call=query.distress_call,
        ),
    )


@router.post("/{session_id}/petcam-events", name="펫캠 사진 업로드 URL 발급")
async def add_petcam_event(
    session: Annotated[Session, Depends(require_session)],
    device: ActiveDevice,
    body: SessionPetcamEventRequest,
    db: DBSession,
    storage: Storage,
) -> SessionPetcamEventUploadResponse:
    return SessionPetcamEventUploadResponse(
        message="펫캠 사진 업로드 URL 발급 성공",
        data=await sessions.add_petcam_event(db=db, storage=storage, session=session, device=device, data=body),
    )


@router.post("/{session_id}/petcam-events/{event_id}/video", name="펫캠 영상 업로드 URL 발급")
async def add_petcam_video(
    session: Annotated[Session, Depends(require_session)],
    device: ActiveDevice,
    event_id: UUID,
    body: SessionPetcamVideoUploadRequest,
    db: DBSession,
    storage: Storage,
) -> UploadResponse:
    return UploadResponse(
        message="펫캠 영상 업로드 URL 발급 성공",
        data=await sessions.add_petcam_video(
            db=db, storage=storage, session=session, device=device, event_id=event_id, data=body
        ),
    )


@router.post("/{session_id}/sounds", name="세션 소리 업로드 URL 발급")
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


@router.get("/{session_id}/sounds", name="세션 소리 목록 조회")
async def get_sounds(
    session: Annotated[Session, Depends(require_session)],
    query: Annotated[SessionSoundListParams, Query()],
    db: DBSession,
    storage: Storage,
) -> SessionSoundListResponse:
    items, total = await session_sounds.get_list(db=db, storage=storage, session=session, query=query)

    return SessionSoundListResponse(
        message="세션 소리 목록 조회 성공",
        data=items,
        meta=query.meta(total),
    )


@router.put("/{session_id}/sounds/{session_sound_id}/user-review", name="세션 소리 리뷰")
async def update_sound_user_review(
    sound: Annotated[SessionSound, Depends(require_session_sound)], body: UpdateSessionUserReviewRequest, db: DBSession
) -> BaseResponse:
    await session_sounds.update_user_review(db=db, sound=sound, data=body)

    return BaseResponse(message="세션 소리 리뷰 성공")


@router.delete("/{session_id}/sounds/{session_sound_id}/user-review", name="세션 소리 리뷰 취소")
async def delete_sound_user_review(
    sound: Annotated[SessionSound, Depends(require_session_sound)], db: DBSession
) -> BaseResponse:
    await session_sounds.delete_user_review(db=db, sound=sound)

    return BaseResponse(message="세션 소리 리뷰 취소 성공")


@router.put("/{session_id}/events/{session_event_id}/user-review", name="세션 이벤트 리뷰")
async def update_event_user_review(
    event: Annotated[SessionEvent, Depends(require_session_event)], body: UpdateSessionUserReviewRequest, db: DBSession
) -> BaseResponse:
    await sessions.update_event_user_review(db=db, event=event, data=body)

    return BaseResponse(message="세션 이벤트 리뷰 성공")


@router.delete("/{session_id}/events/{session_event_id}/user-review", name="세션 이벤트 리뷰 취소")
async def delete_event_user_review(
    event: Annotated[SessionEvent, Depends(require_session_event)], db: DBSession
) -> BaseResponse:
    await sessions.delete_event_user_review(db=db, event=event)

    return BaseResponse(message="세션 이벤트 리뷰 취소 성공")


@router.get("/{session_id}/summary", name="세션 요약 조회")
async def get_summary(session: Annotated[Session, Depends(require_session)], db: DBSession) -> SessionSummaryResponse:
    return SessionSummaryResponse(
        message="세션 요약 조회 성공", data=await sessions.get_summary(db=db, session=session)
    )

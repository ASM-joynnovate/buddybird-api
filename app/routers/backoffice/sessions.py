from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import DBSession, require_backoffice_session
from app.models import Session
from app.schemas.base import BaseResponse
from app.schemas.sessions import BackofficeSessionEventListResponse, BackofficeSessionSoundListResponse
from app.services import session_sounds, sessions

router = APIRouter(prefix="/sessions")


@router.post("/ended-reasons/backfill", name="세션 종료 사유 채우기")
async def backfill_ended_reasons(db: DBSession) -> BaseResponse:
    await sessions.backfill_ended_reasons(db=db)

    return BaseResponse(message="세션 종료 사유 채우기 성공")


@router.get("/{session_id}/events", name="세션 이벤트 조회")
async def get_events(
    session: Annotated[Session, Depends(require_backoffice_session)], db: DBSession
) -> BackofficeSessionEventListResponse:
    return BackofficeSessionEventListResponse(
        message="세션 이벤트 조회 성공",
        data=await sessions.get_backoffice_events(db=db, session=session),
    )


@router.get("/{session_id}/sounds", name="세션 소리 시각 조회")
async def get_sounds(
    session: Annotated[Session, Depends(require_backoffice_session)], db: DBSession
) -> BackofficeSessionSoundListResponse:
    return BackofficeSessionSoundListResponse(
        message="세션 소리 시각 조회 성공",
        data=await session_sounds.get_backoffice_list(db=db, session=session),
    )

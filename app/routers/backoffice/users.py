from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import DBSession, Storage, require_backoffice_user
from app.models import User
from app.schemas.base import PageParams
from app.schemas.sessions import SessionListResponse
from app.schemas.users import BackofficeUserDetailResponse, BackofficeUserListParams, BackofficeUserListResponse
from app.services import sessions, users

router = APIRouter(prefix="/users")


@router.get("", name="사용자 목록 조회")
async def get_list(query: Annotated[BackofficeUserListParams, Query()], db: DBSession) -> BackofficeUserListResponse:
    items, total = await users.get_backoffice_list(db=db, query=query)

    return BackofficeUserListResponse(
        message="사용자 목록 조회 성공",
        data=items,
        meta=query.meta(total),
    )


@router.get("/{user_id}", name="사용자 상세 조회")
async def get_detail(
    user: Annotated[User, Depends(require_backoffice_user)], db: DBSession, storage: Storage
) -> BackofficeUserDetailResponse:
    return BackofficeUserDetailResponse(
        message="사용자 상세 조회 성공",
        data=await users.get_backoffice_detail(db=db, storage=storage, user=user),
    )


@router.get("/{user_id}/sessions", name="사용자 세션 목록 조회")
async def get_sessions(
    user: Annotated[User, Depends(require_backoffice_user)], query: Annotated[PageParams, Query()], db: DBSession
) -> SessionListResponse:
    items, total = await sessions.get_list(db=db, user=user, query=query)

    return SessionListResponse(
        message="사용자 세션 목록 조회 성공",
        data=items,
        meta=query.meta(total),
    )

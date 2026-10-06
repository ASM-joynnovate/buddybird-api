from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.dependencies import DBSession, Storage, require_backoffice_user
from app.models import User
from app.schemas.base import PageParams
from app.schemas.sessions import SessionListResponse
from app.schemas.users import BackofficeUserDetailResponse, BackofficeUserListParams, BackofficeUserListResponse
from app.schemas.withdrawals import WithdrawalResponse
from app.services import sessions, users, withdrawals

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


@router.delete("/{user_id}", name="사용자 삭제", status_code=202)
async def delete(
    user: Annotated[User, Depends(require_backoffice_user)], db: DBSession, background_tasks: BackgroundTasks
) -> WithdrawalResponse:
    data = await withdrawals.request_backoffice_withdrawal(db=db, auth_user_id=user.auth_user_id)
    background_tasks.add_task(withdrawals.enqueue_withdrawal, data.user_id)

    return WithdrawalResponse(message="사용자 삭제 요청이 접수되었습니다.", data=data)


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

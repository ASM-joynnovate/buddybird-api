from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.dependencies import DBSession, Storage, require_backoffice_user
from app.models import User
from app.schemas.base import PageParams
from app.schemas.consents import BackofficeUserConsentListResponse
from app.schemas.sessions import BackofficeSessionListResponse
from app.schemas.users import BackofficeUserDetailResponse, BackofficeUserListParams, BackofficeUserListResponse
from app.schemas.withdrawals import WithdrawalResponse
from app.schemas.words import BackofficeWordListResponse
from app.services import sessions, user_consents, users, withdrawals, words

router = APIRouter(prefix="/users")


@router.get("", name="사용자 목록 조회")
async def get_list(
    query: Annotated[BackofficeUserListParams, Query()], db: DBSession, storage: Storage
) -> BackofficeUserListResponse:
    items, total = await users.get_backoffice_list(db=db, storage=storage, query=query)

    return BackofficeUserListResponse(
        message="사용자 목록 조회 성공",
        data=items,
        meta={**query.meta(total), "total_count": total},
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
) -> BackofficeSessionListResponse:
    items, total = await sessions.get_backoffice_list(db=db, user=user, query=query)

    return BackofficeSessionListResponse(
        message="사용자 세션 목록 조회 성공",
        data=items,
        meta={**query.meta(total), "total_count": total},
    )


@router.get("/{user_id}/words", name="사용자 단어 목록 조회")
async def get_words(
    user: Annotated[User, Depends(require_backoffice_user)], db: DBSession, storage: Storage
) -> BackofficeWordListResponse:
    return BackofficeWordListResponse(
        message="사용자 단어 목록 조회 성공",
        data=await words.get_backoffice_list(db=db, user=user, storage=storage),
    )


@router.get("/{user_id}/consents", name="사용자 동의 내역 조회")
async def get_consents(
    user: Annotated[User, Depends(require_backoffice_user)], db: DBSession
) -> BackofficeUserConsentListResponse:
    return BackofficeUserConsentListResponse(
        message="사용자 동의 내역 조회 성공",
        data=await user_consents.get_backoffice_list(db=db, user=user),
    )

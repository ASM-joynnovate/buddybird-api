from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header

from app.dependencies import ActiveUser, Authenticated, DBSession, Storage
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.base import BaseResponse
from app.schemas.withdrawals import WithdrawalResponse
from app.services import auth, notifications, withdrawals

router = APIRouter(prefix="/auth")


@router.post("/login", name="로그인 완료")
async def login(
    context: Authenticated, db: DBSession, storage: Storage, body: LoginRequest | None = None
) -> LoginResponse:
    return LoginResponse(
        message="로그인 성공",
        data=await auth.complete_login(
            db=db,
            storage=storage,
            auth_user_id=context.auth_user_id,
            access_token=context.access_token,
            is_anonymous=context.is_anonymous,
            data=body,
        ),
    )


@router.post("/logout", name="로그아웃")
async def logout(
    user: ActiveUser,
    db: DBSession,
    x_device_id: Annotated[UUID | None, Header(alias="X-Device-Id")] = None,
) -> BaseResponse:
    session_ids = await auth.logout(db=db, user=user, client_device_id=x_device_id)

    await notifications.send_report(db=db, session_ids=session_ids)

    return BaseResponse(message="로그아웃 성공")


@router.delete("/withdrawal", name="회원 탈퇴 접수", status_code=202)
async def withdrawal(context: Authenticated, db: DBSession, background_tasks: BackgroundTasks) -> WithdrawalResponse:
    data = await withdrawals.request_withdrawal(
        db=db, auth_user_id=context.auth_user_id, access_token=context.access_token
    )
    background_tasks.add_task(withdrawals.enqueue_withdrawal, data.user_id)

    return WithdrawalResponse(message="탈퇴 요청이 접수되었습니다.", data=data)

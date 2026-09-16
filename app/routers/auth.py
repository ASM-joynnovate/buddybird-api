from fastapi import APIRouter, BackgroundTasks

from app.dependencies import Authenticated, DBSession, Storage
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.withdrawals import WithdrawalResponse
from app.services import auth, withdrawals
from app.tasks import enqueue_withdrawal

router = APIRouter(prefix="/auth")


@router.post("/login", name="로그인 완료", response_model=LoginResponse)
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
            data=body,
        ),
    )


@router.delete("/withdrawal", name="회원 탈퇴 접수", status_code=202, response_model=WithdrawalResponse)
async def withdrawal(context: Authenticated, db: DBSession, background_tasks: BackgroundTasks) -> WithdrawalResponse:
    data = await withdrawals.request_withdrawal(
        db=db, auth_user_id=context.auth_user_id, access_token=context.access_token
    )
    background_tasks.add_task(enqueue_withdrawal, data.user_id)

    return WithdrawalResponse(message="탈퇴 요청이 접수되었습니다.", data=data)

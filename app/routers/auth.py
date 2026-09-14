from fastapi import APIRouter

from app import auth
from app.dependencies import Authenticated, DBSession, Storage
from app.schemas import LoginResponse

router = APIRouter(prefix="/auth")


@router.post("/login", name="로그인 완료", response_model=LoginResponse)
async def login(context: Authenticated, db: DBSession, storage: Storage) -> LoginResponse:
    return LoginResponse(
        message="로그인 성공",
        data=await auth.complete_login(context=context, db=db, storage=storage),
    )

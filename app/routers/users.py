from typing import Annotated

from fastapi import APIRouter, File, UploadFile

from app import users
from app.dependencies import ActiveUser, DBSession, Storage
from app.schemas import BaseResponse, UpdateUserRequest, UserResponse

router = APIRouter(prefix="/users")


@router.get("/me", name="내 프로필 조회", response_model=UserResponse)
async def get_me(context: ActiveUser, db: DBSession, storage: Storage) -> UserResponse:
    return UserResponse(
        message="사용자 조회 성공",
        data=await users.get_profile(user_id=context.user_id, db=db, storage=storage),
    )


@router.patch("/me", name="내 프로필 수정")
async def update_me(context: ActiveUser, body: UpdateUserRequest, db: DBSession) -> BaseResponse:
    await users.update_profile(user_id=context.user_id, data=body, db=db)
    return BaseResponse(message="사용자 수정 성공")


@router.put("/me/photo", name="내 프로필 사진 수정")
async def update_photo(
    context: ActiveUser,
    file: Annotated[UploadFile, File(description="프로필 사진")],
    db: DBSession,
    storage: Storage,
) -> BaseResponse:
    await users.update_photo(user_id=context.user_id, file=file, db=db, storage=storage)
    return BaseResponse(message="프로필 사진 수정 성공")


@router.delete("/me/photo", name="내 프로필 사진 삭제")
async def delete_photo(context: ActiveUser, db: DBSession) -> BaseResponse:
    await users.delete_photo(user_id=context.user_id, db=db)
    return BaseResponse(message="프로필 사진 삭제 성공")

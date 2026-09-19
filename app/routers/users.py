from fastapi import APIRouter

from app.dependencies import ActiveUser, DBSession, Storage
from app.schemas.base import BaseResponse, UploadRequest, UploadResponse
from app.schemas.users import UpdateUserRequest, UserResponse
from app.services import users

router = APIRouter(prefix="/users")


@router.get("/me", name="내 프로필 조회", response_model=UserResponse)
async def get_me(user: ActiveUser, storage: Storage) -> UserResponse:
    return UserResponse(message="사용자 조회 성공", data=await users.get_profile(user=user, storage=storage))


@router.patch("/me", name="내 프로필 수정")
async def update_me(user: ActiveUser, body: UpdateUserRequest, db: DBSession) -> BaseResponse:
    await users.update_profile(db=db, user=user, data=body)

    return BaseResponse(message="사용자 수정 성공")


@router.put("/me/photo", name="내 프로필 사진 업로드 URL 발급", response_model=UploadResponse)
async def update_photo(user: ActiveUser, body: UploadRequest, db: DBSession, storage: Storage) -> UploadResponse:
    return UploadResponse(
        message="프로필 사진 업로드 URL 발급 성공",
        data=await users.update_photo(db=db, storage=storage, user=user, data=body),
    )


@router.delete("/me/photo", name="내 프로필 사진 삭제")
async def delete_photo(user: ActiveUser, db: DBSession) -> BaseResponse:
    await users.delete_photo(db=db, user=user)

    return BaseResponse(message="프로필 사진 삭제 성공")

from uuid import UUID

from fastapi import APIRouter

from app.dependencies import ActiveUser, DBSession, Storage
from app.schemas.base import BaseResponse
from app.schemas.users import BlockedUserListResponse
from app.services import user_blocks

router = APIRouter(prefix="/users/me/blocks")


@router.get("", name="차단 목록 조회")
async def get_list(user: ActiveUser, db: DBSession, storage: Storage) -> BlockedUserListResponse:
    return BlockedUserListResponse(
        message="차단 목록 조회 성공", data=await user_blocks.get_list(db=db, storage=storage, user=user)
    )


@router.put("/{user_id}", name="사용자 차단")
async def block(user: ActiveUser, user_id: UUID, db: DBSession) -> BaseResponse:
    await user_blocks.block(db=db, user=user, blocked_user_id=user_id)

    return BaseResponse(message="사용자 차단 성공")


@router.delete("/{user_id}", name="사용자 차단 해제")
async def unblock(user: ActiveUser, user_id: UUID, db: DBSession) -> BaseResponse:
    await user_blocks.unblock(db=db, user=user, blocked_user_id=user_id)

    return BaseResponse(message="사용자 차단 해제 성공")

from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import ActiveUser, DBSession, Storage
from app.schemas.base import PageParams
from app.schemas.sessions import SessionSoundListResponse
from app.services import session_sounds

router = APIRouter(prefix="/users/me/parrot-sounds")


@router.get("", name="내 앵무새 발성 목록 조회")
async def get_list(
    user: ActiveUser, query: Annotated[PageParams, Query()], db: DBSession, storage: Storage
) -> SessionSoundListResponse:
    items, total = await session_sounds.get_user_list(db=db, storage=storage, user=user, query=query)

    return SessionSoundListResponse(
        message="앵무새 발성 목록 조회 성공",
        data=items,
        meta=query.meta(total),
    )

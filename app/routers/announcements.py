from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import ActiveUser, DBSession, Locale, Storage, require_announcement
from app.models import Announcement
from app.schemas.announcements import AnnouncementListResponse, AnnouncementResponse
from app.schemas.base import PageParams
from app.services import announcements

router = APIRouter(prefix="/announcements")


@router.get("", name="공지 목록 조회")
async def get_list(
    user: ActiveUser, locale: Locale, query: Annotated[PageParams, Query()], db: DBSession, storage: Storage
) -> AnnouncementListResponse:
    items, total = await announcements.get_list(db=db, user=user, locale=locale, storage=storage, query=query)

    return AnnouncementListResponse(
        message="공지 목록 조회 성공",
        data=items,
        meta=query.meta(total),
    )


@router.get("/{announcement_id}", name="공지 상세 조회")
async def get_detail(
    user: ActiveUser,
    locale: Locale,
    announcement: Annotated[Announcement, Depends(require_announcement)],
    db: DBSession,
    storage: Storage,
) -> AnnouncementResponse:
    return AnnouncementResponse(
        message="공지 상세 조회 성공",
        data=await announcements.get_detail(
            db=db, user=user, locale=locale, storage=storage, announcement=announcement
        ),
    )


@router.post("/{announcement_id}/read", name="공지 읽음 처리")
async def mark_read(
    user: ActiveUser,
    locale: Locale,
    announcement: Annotated[Announcement, Depends(require_announcement)],
    db: DBSession,
    storage: Storage,
) -> AnnouncementResponse:
    return AnnouncementResponse(
        message="공지 읽음 처리 성공",
        data=await announcements.mark_read(db=db, user=user, locale=locale, storage=storage, announcement=announcement),
    )

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import DBSession, Storage, require_announcement, require_announcement_image
from app.models import Announcement, AnnouncementImage
from app.schemas.announcements import (
    BackofficeAnnouncementListResponse,
    BackofficeAnnouncementResponse,
    CreateAnnouncementRequest,
    UpdateAnnouncementRequest,
)
from app.schemas.base import BaseResponse, PageParams, UploadRequest, UploadResponse
from app.services import announcements

router = APIRouter(prefix="/announcements")


@router.get("", name="공지 목록 조회")
async def get_list(
    query: Annotated[PageParams, Query()], db: DBSession, storage: Storage
) -> BackofficeAnnouncementListResponse:
    items, total = await announcements.get_backoffice_list(db=db, storage=storage, query=query)

    return BackofficeAnnouncementListResponse(
        message="공지 목록 조회 성공",
        data=items,
        meta=query.meta(total),
    )


@router.post("", name="공지 생성")
async def create(body: CreateAnnouncementRequest, db: DBSession, storage: Storage) -> BackofficeAnnouncementResponse:
    return BackofficeAnnouncementResponse(
        message="공지 생성 성공", data=await announcements.create(db=db, storage=storage, data=body)
    )


@router.patch("/{announcement_id}", name="공지 수정")
async def update(
    announcement: Annotated[Announcement, Depends(require_announcement)],
    body: UpdateAnnouncementRequest,
    db: DBSession,
    storage: Storage,
) -> BackofficeAnnouncementResponse:
    return BackofficeAnnouncementResponse(
        message="공지 수정 성공",
        data=await announcements.update(db=db, storage=storage, announcement=announcement, data=body),
    )


@router.delete("/{announcement_id}", name="공지 삭제")
async def delete(announcement: Annotated[Announcement, Depends(require_announcement)], db: DBSession) -> BaseResponse:
    await announcements.delete(db=db, announcement=announcement)

    return BaseResponse(message="공지 삭제 성공")


@router.post("/{announcement_id}/images", name="공지 사진 업로드 URL 발급")
async def add_image(
    announcement: Annotated[Announcement, Depends(require_announcement)],
    body: UploadRequest,
    db: DBSession,
    storage: Storage,
) -> UploadResponse:
    return UploadResponse(
        message="공지 사진 업로드 URL 발급 성공",
        data=await announcements.add_image(db=db, storage=storage, announcement=announcement, data=body),
    )


@router.delete("/{announcement_id}/images/{image_id}", name="공지 사진 삭제")
async def delete_image(
    announcement: Annotated[Announcement, Depends(require_announcement)],
    image: Annotated[AnnouncementImage, Depends(require_announcement_image)],
    db: DBSession,
    storage: Storage,
) -> BackofficeAnnouncementResponse:
    return BackofficeAnnouncementResponse(
        message="공지 사진 삭제 성공",
        data=await announcements.delete_image(db=db, storage=storage, announcement=announcement, image=image),
    )

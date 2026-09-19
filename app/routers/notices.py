from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import ActiveUser, DBSession, Storage, require_backoffice, require_notice, require_notice_image
from app.models import Notice, NoticeImage
from app.schemas.base import BaseResponse, PageParams, UploadRequest, UploadResponse
from app.schemas.notices import CreateNoticeRequest, NoticeListResponse, NoticeResponse, UpdateNoticeRequest
from app.services import notices

router = APIRouter(prefix="/notices")


@router.get("", name="공지 목록 조회", response_model=NoticeListResponse)
async def get_list(
    user: ActiveUser, query: Annotated[PageParams, Query()], db: DBSession, storage: Storage
) -> NoticeListResponse:
    items, total = await notices.get_list(db=db, user=user, storage=storage, query=query)

    return NoticeListResponse(
        message="공지 목록 조회 성공",
        data=items,
        meta={
            "current_page": query.page,
            "total_page_count": (total + query.count_by_page - 1) // query.count_by_page,
            "is_first": query.page == 1,
            "is_last": query.page * query.count_by_page >= total,
        },
    )


@router.get("/{notice_id}", name="공지 상세 조회", response_model=NoticeResponse)
async def get_detail(
    user: ActiveUser, notice: Annotated[Notice, Depends(require_notice)], db: DBSession, storage: Storage
) -> NoticeResponse:
    return NoticeResponse(
        message="공지 상세 조회 성공", data=await notices.get_detail(db=db, user=user, storage=storage, notice=notice)
    )


@router.post("/{notice_id}/read", name="공지 읽음 처리", response_model=NoticeResponse)
async def mark_read(
    user: ActiveUser, notice: Annotated[Notice, Depends(require_notice)], db: DBSession, storage: Storage
) -> NoticeResponse:
    return NoticeResponse(
        message="공지 읽음 처리 성공", data=await notices.mark_read(db=db, user=user, storage=storage, notice=notice)
    )


@router.post("", name="공지 생성", response_model=NoticeResponse, dependencies=[Depends(require_backoffice)])
async def create(body: CreateNoticeRequest, db: DBSession, storage: Storage) -> NoticeResponse:
    return NoticeResponse(message="공지 생성 성공", data=await notices.create(db=db, storage=storage, data=body))


@router.patch(
    "/{notice_id}", name="공지 수정", response_model=NoticeResponse, dependencies=[Depends(require_backoffice)]
)
async def update(
    notice: Annotated[Notice, Depends(require_notice)], body: UpdateNoticeRequest, db: DBSession, storage: Storage
) -> NoticeResponse:
    return NoticeResponse(
        message="공지 수정 성공", data=await notices.update(db=db, storage=storage, notice=notice, data=body)
    )


@router.delete("/{notice_id}", name="공지 삭제", dependencies=[Depends(require_backoffice)])
async def delete(notice: Annotated[Notice, Depends(require_notice)], db: DBSession) -> BaseResponse:
    await notices.delete(db=db, notice=notice)

    return BaseResponse(message="공지 삭제 성공")


@router.post(
    "/{notice_id}/images",
    name="공지 사진 업로드 URL 발급",
    response_model=UploadResponse,
    dependencies=[Depends(require_backoffice)],
)
async def add_image(
    notice: Annotated[Notice, Depends(require_notice)],
    body: UploadRequest,
    db: DBSession,
    storage: Storage,
) -> UploadResponse:
    return UploadResponse(
        message="공지 사진 업로드 URL 발급 성공",
        data=await notices.add_image(db=db, storage=storage, notice=notice, data=body),
    )


@router.delete(
    "/{notice_id}/images/{image_id}",
    name="공지 사진 삭제",
    response_model=NoticeResponse,
    dependencies=[Depends(require_backoffice)],
)
async def delete_image(
    notice: Annotated[Notice, Depends(require_notice)],
    image: Annotated[NoticeImage, Depends(require_notice_image)],
    db: DBSession,
    storage: Storage,
) -> NoticeResponse:
    return NoticeResponse(
        message="공지 사진 삭제 성공",
        data=await notices.delete_image(db=db, storage=storage, notice=notice, image=image),
    )

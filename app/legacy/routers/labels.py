from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import DBSession
from app.legacy.dependencies import verify_backoffice_password
from app.legacy.schemas.labels import (
    CreateLabelCategoryRequest,
    CreateLabelOptionRequest,
    GetLabelListResponse,
    UpdateLabelCategoryRequest,
    UpdateLabelOptionRequest,
)
from app.legacy.services import labels
from app.schemas.base import BaseResponse

router = APIRouter(dependencies=[Depends(verify_backoffice_password)])


@router.get("/labels", name="라벨 목록 조회", response_model=GetLabelListResponse)
async def get_labels(db: DBSession) -> BaseResponse:
    return BaseResponse(message="라벨 목록 조회 성공", data=await labels.get_label_list(db=db))


@router.post("/labels/categories", name="라벨 카테고리 생성")
async def create_label_category(body: CreateLabelCategoryRequest, db: DBSession) -> BaseResponse:
    return BaseResponse(message="라벨 카테고리 생성 성공", data=await labels.create_label_category(data=body, db=db))


@router.patch("/labels/categories/{label_category_id:uuid}", name="라벨 카테고리 수정")
async def update_label_category(
    label_category_id: UUID, body: UpdateLabelCategoryRequest, db: DBSession
) -> BaseResponse:
    return BaseResponse(
        message="라벨 카테고리 수정 성공",
        data=await labels.update_label_category(label_category_id=label_category_id, data=body, db=db),
    )


@router.delete("/labels/categories/{label_category_id:uuid}", name="라벨 카테고리 삭제")
async def delete_label_category(label_category_id: UUID, db: DBSession) -> BaseResponse:
    return BaseResponse(
        message="라벨 카테고리 삭제 성공",
        data=await labels.delete_label_category(label_category_id=label_category_id, db=db),
    )


@router.post("/labels/categories/{label_category_id:uuid}/options", name="라벨 옵션 생성")
async def create_label_option(label_category_id: UUID, body: CreateLabelOptionRequest, db: DBSession) -> BaseResponse:
    return BaseResponse(
        message="라벨 옵션 생성 성공",
        data=await labels.create_label_option(label_category_id=label_category_id, data=body, db=db),
    )


@router.patch("/labels/options/{label_option_id:uuid}", name="라벨 옵션 수정")
async def update_label_option(label_option_id: UUID, body: UpdateLabelOptionRequest, db: DBSession) -> BaseResponse:
    return BaseResponse(
        message="라벨 옵션 수정 성공",
        data=await labels.update_label_option(label_option_id=label_option_id, data=body, db=db),
    )


@router.delete("/labels/options/{label_option_id:uuid}", name="라벨 옵션 삭제")
async def delete_label_option(label_option_id: UUID, db: DBSession) -> BaseResponse:
    return BaseResponse(
        message="라벨 옵션 삭제 성공", data=await labels.delete_label_option(label_option_id=label_option_id, db=db)
    )

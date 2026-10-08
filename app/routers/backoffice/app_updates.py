from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.dependencies import DBSession, require_app_update
from app.models import AppUpdate
from app.schemas.app_updates import (
    BackofficeAppUpdateListParams,
    BackofficeAppUpdateListResponse,
    BackofficeAppUpdateResponse,
    CreateAppUpdateRequest,
    UpdateAppUpdateRequest,
)
from app.services import app_updates

router = APIRouter(prefix="/app-updates")


@router.get("", name="앱 업데이트 목록 조회")
async def get_list(
    query: Annotated[BackofficeAppUpdateListParams, Query()], db: DBSession
) -> BackofficeAppUpdateListResponse:
    return BackofficeAppUpdateListResponse(
        message="앱 업데이트 목록 조회 성공",
        data=await app_updates.get_backoffice_list(db=db, query=query),
    )


@router.post("", name="앱 업데이트 추가")
async def create(body: CreateAppUpdateRequest, db: DBSession) -> BackofficeAppUpdateResponse:
    return BackofficeAppUpdateResponse(
        message="앱 업데이트 추가 성공",
        data=await app_updates.create(db=db, data=body),
    )


@router.patch("/{app_update_id}", name="앱 업데이트 수정")
async def update(
    app_update: Annotated[AppUpdate, Depends(require_app_update)], body: UpdateAppUpdateRequest, db: DBSession
) -> BackofficeAppUpdateResponse:
    return BackofficeAppUpdateResponse(
        message="앱 업데이트 수정 성공",
        data=await app_updates.update(db=db, app_update=app_update, data=body),
    )

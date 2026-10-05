from fastapi import APIRouter

from app.dependencies import DBSession
from app.enums import PlatformEnum
from app.schemas.app_updates import BackofficeAppUpdateResponse, SaveAppUpdateRequest
from app.services import app_updates

router = APIRouter(prefix="/app-updates")


@router.get("/{platform}", name="앱 업데이트 정보 조회")
async def get_detail(platform: PlatformEnum, db: DBSession) -> BackofficeAppUpdateResponse:
    return BackofficeAppUpdateResponse(
        message="앱 업데이트 정보 조회 성공",
        data=await app_updates.get_backoffice_detail(db=db, platform=platform),
    )


@router.put("/{platform}", name="앱 업데이트 정보 저장")
async def save(platform: PlatformEnum, body: SaveAppUpdateRequest, db: DBSession) -> BackofficeAppUpdateResponse:
    return BackofficeAppUpdateResponse(
        message="앱 업데이트 정보 저장 성공",
        data=await app_updates.save(db=db, platform=platform, data=body),
    )

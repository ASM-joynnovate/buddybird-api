from fastapi import APIRouter, Depends

from app.dependencies import DBSession, Locale, require_active_user
from app.enums import PlatformEnum
from app.schemas.app_updates import AppUpdateResponse
from app.services import app_updates

router = APIRouter(prefix="/app-updates")


@router.get("/{platform}", name="앱 업데이트 정보 조회", dependencies=[Depends(require_active_user)])
async def get_detail(platform: PlatformEnum, locale: Locale, db: DBSession) -> AppUpdateResponse:
    return AppUpdateResponse(
        message="앱 업데이트 정보 조회 성공",
        data=await app_updates.get_detail(db=db, platform=platform, locale=locale),
    )

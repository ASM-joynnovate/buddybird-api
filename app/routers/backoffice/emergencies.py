from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import DBSession, Storage
from app.schemas.emergencies import BackofficeEmergencyListParams, BackofficeEmergencyListResponse
from app.services import emergencies

router = APIRouter(prefix="/emergencies")


@router.get("", name="응급 상황 목록 조회")
async def get_list(
    query: Annotated[BackofficeEmergencyListParams, Query()], db: DBSession, storage: Storage
) -> BackofficeEmergencyListResponse:
    items, total = await emergencies.get_backoffice_list(db=db, storage=storage, query=query)

    return BackofficeEmergencyListResponse(
        message="응급 상황 목록 조회 성공",
        data=items,
        meta={**query.meta(total), "total_count": total},
    )

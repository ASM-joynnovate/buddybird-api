from typing import Annotated

from fastapi import APIRouter, Query

from app.dependencies import DBSession
from app.schemas.withdrawals import BackofficeWithdrawalListParams, BackofficeWithdrawalListResponse
from app.services import withdrawals

router = APIRouter(prefix="/withdrawals")


@router.get("", name="탈퇴 처리 현황 조회")
async def get_list(
    query: Annotated[BackofficeWithdrawalListParams, Query()], db: DBSession
) -> BackofficeWithdrawalListResponse:
    items, total = await withdrawals.get_backoffice_list(db=db, query=query)

    return BackofficeWithdrawalListResponse(
        message="탈퇴 처리 현황 조회 성공",
        data=items,
        meta=query.meta(total),
    )

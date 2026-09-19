from uuid import UUID

from app.schemas.base import BaseResponse, CustomBaseModel


class WithdrawalDTO(CustomBaseModel):
    user_id: UUID


class WithdrawalResponse(BaseResponse):
    data: WithdrawalDTO

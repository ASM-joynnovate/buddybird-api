from datetime import datetime
from uuid import UUID

from pydantic import field_validator

from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class FeedbackDTO(CustomBaseModel):
    id: UUID
    user_id: UUID
    device_id: UUID
    message: str
    app_version: str
    created_at: datetime


class FeedbackResponse(BaseResponse):
    data: FeedbackDTO


class FeedbackListResponse(BaseResponse):
    data: list[FeedbackDTO]


class CreateFeedbackRequest(BaseRequest):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()

        if not 1 <= len(value) <= 1000:
            raise ValueError("메시지는 1~1000자여야 합니다.")

        return value

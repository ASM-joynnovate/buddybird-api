from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import StringConstraints

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
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]

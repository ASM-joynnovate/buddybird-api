from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import Field

from app.enums import FeedItemKindEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, PublicFileDTO
from app.schemas.users import CommunityUserDTO


class FeedParams(BaseRequest):
    cursor: UUID | None = None
    count_by_page: int = Field(12, ge=1, le=100)
    kind: FeedItemKindEnum | None = None
    country: str | None = Field(None, pattern=r"^[A-Z]{2}$")
    user_id: UUID | None = None


class FeedItemLikeDTO(CustomBaseModel):
    like_count: int
    is_liked: bool


class FeedItemLikeResponse(BaseResponse):
    data: FeedItemLikeDTO


class FeedItemDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word_name", "file", "threshold"}

    id: UUID
    kind: FeedItemKindEnum
    created_at: datetime
    user: CommunityUserDTO
    word_name: str | None
    file: PublicFileDTO | None
    threshold: int | None
    like_count: int
    is_liked: bool


class FeedResponse(BaseResponse):
    data: list[FeedItemDTO]

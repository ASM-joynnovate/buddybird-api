from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import Field
from pydantic.experimental.missing_sentinel import MISSING

from app.enums import FeedItemKindEnum
from app.schemas.base import (
    BaseRequest,
    BaseResponse,
    CustomBaseModel,
    FileDTO,
    I18nDTO,
    I18nTitleRequest,
    PublicFileDTO,
    UpdateI18nTitleRequest,
)
from app.schemas.users import CommunityUserDTO


class FeedParams(BaseRequest):
    cursor: UUID | None = None
    count_by_page: int = Field(12, ge=1, le=100)
    kind: FeedItemKindEnum | None = None
    country: str | None = Field(None, pattern=r"^[A-Z]{2}$")
    user_id: UUID | None = None


class FeedItemReactionDTO(CustomBaseModel):
    reaction_type_id: UUID
    count: int
    is_mine: bool


class FeedItemDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word_name", "file", "threshold"}

    id: UUID
    kind: FeedItemKindEnum
    created_at: datetime
    user: CommunityUserDTO
    word_name: str | None
    file: PublicFileDTO | None
    threshold: int | None
    reactions: list[FeedItemReactionDTO]


class FeedResponse(BaseResponse):
    data: list[FeedItemDTO]


class FeedReactionTypeDTO(CustomBaseModel):
    id: UUID
    name: str
    image_file: PublicFileDTO


class FeedReactionTypeListResponse(BaseResponse):
    data: list[FeedReactionTypeDTO]


class BackofficeFeedReactionTypeDTO(CustomBaseModel):
    id: UUID
    name: I18nDTO
    image_file: FileDTO
    sort_order: int


class BackofficeFeedReactionTypeResponse(BaseResponse):
    data: BackofficeFeedReactionTypeDTO


class BackofficeFeedReactionTypeListResponse(BaseResponse):
    data: list[BackofficeFeedReactionTypeDTO]


class CreateFeedReactionTypeRequest(BaseRequest):
    name: I18nTitleRequest
    image_file_id: UUID


class UpdateFeedReactionTypeRequest(BaseRequest):
    name: UpdateI18nTitleRequest | MISSING = MISSING
    image_file_id: UUID | MISSING = MISSING

from datetime import datetime
from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import StringConstraints

from app.enums import AbuseReportReasonEnum, FeedItemKindEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, FileDTO, PageParams
from app.schemas.users import BackofficeUserDTO


class CreateAbuseReportRequest(BaseRequest):
    null_fields: ClassVar[set] = {"feed_item_id", "description"}

    reported_user_id: UUID
    feed_item_id: UUID | None = None
    reason: AbuseReportReasonEnum
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)] | None = None


class BackofficeAbuseReportListParams(PageParams):
    is_handled: bool | None = None


class BackofficeAbuseReportFeedItemDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word_name", "file", "threshold"}

    id: UUID
    kind: FeedItemKindEnum
    word_name: str | None
    file: FileDTO | None
    threshold: int | None
    is_deleted: bool


class BackofficeAbuseReportDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"feed_item", "description", "handled_at"}

    id: UUID
    reporter: BackofficeUserDTO
    reported_user: BackofficeUserDTO
    feed_item: BackofficeAbuseReportFeedItemDTO | None
    reason: AbuseReportReasonEnum
    description: str | None
    handled_at: datetime | None
    created_at: datetime


class BackofficeAbuseReportListResponse(BaseResponse):
    data: list[BackofficeAbuseReportDTO]

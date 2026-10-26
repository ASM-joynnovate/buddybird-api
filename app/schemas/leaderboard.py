from typing import ClassVar

from pydantic import Field

from app.enums import LeaderboardPeriodEnum, LeaderboardUnrankedReasonEnum, ScoreMetricEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel
from app.schemas.users import CommunityUserDTO


class LeaderboardParams(BaseRequest):
    period: LeaderboardPeriodEnum
    metric: ScoreMetricEnum
    country: str | None = Field(None, pattern=r"^[A-Z]{2}$")


class LeaderboardItemDTO(CustomBaseModel):
    rank: int
    score: int
    user: CommunityUserDTO


class LeaderboardMeDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"rank", "unranked_reason"}

    rank: int | None
    unranked_reason: LeaderboardUnrankedReasonEnum | None
    score: int


class LeaderboardDTO(CustomBaseModel):
    items: list[LeaderboardItemDTO]
    me: LeaderboardMeDTO


class LeaderboardResponse(BaseResponse):
    data: LeaderboardDTO


class ScoreBackfillDTO(CustomBaseModel):
    inserted_count: int


class ScoreBackfillResponse(BaseResponse):
    data: ScoreBackfillDTO

from datetime import UTC, date, datetime
from typing import ClassVar

from pydantic import Field, field_validator

from app.enums import LeaderboardPeriodEnum, LeaderboardUnrankedReasonEnum, ScoreMetricEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel
from app.schemas.users import CommunityUserDTO


class LeaderboardParams(BaseRequest):
    period: LeaderboardPeriodEnum
    metric: ScoreMetricEnum
    country: str | None = Field(None, pattern=r"^[A-Z]{2}$")
    start: date | None = None
    limit: int = Field(50, ge=1, le=50)

    @field_validator("start")
    @classmethod
    def validate_start(cls, value: date | None) -> date | None:
        if value is not None and value.replace(day=1) > datetime.now(UTC).date().replace(day=1):
            raise ValueError("미래의 달은 조회할 수 없습니다.")

        return value


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

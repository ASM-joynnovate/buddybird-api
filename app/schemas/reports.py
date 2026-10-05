from datetime import date, datetime
from typing import ClassVar
from uuid import UUID

from app.enums import ReportPeriodEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel
from app.schemas.sessions import ActiveDurationDTO, SessionJudgmentDTO


class ReportPeriodDTO(CustomBaseModel):
    unit: ReportPeriodEnum
    start: date
    end: date


class ReportTrendDTO(CustomBaseModel):
    start: datetime
    duration_ms: int


class ReportWordDTO(CustomBaseModel):
    id: UUID
    name: str


class ReportWordActiveDTO(CustomBaseModel):
    word: ReportWordDTO
    duration_ms: int


class ReportActiveDTO(CustomBaseModel):
    duration_ms: int
    trend: list[ReportTrendDTO]
    words: list[ReportWordActiveDTO]


class ReportSoundsDTO(CustomBaseModel):
    parrot_count: int
    mimicry_count: int


class ReportSessionPeriodDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"ended_at"}

    started_at: datetime
    ended_at: datetime | None


class ReportSessionSoundsDTO(CustomBaseModel):
    parrot_count: int


class ReportSessionDTO(CustomBaseModel):
    id: UUID
    period: ReportSessionPeriodDTO
    word: ReportWordDTO
    active: ActiveDurationDTO
    sounds: ReportSessionSoundsDTO
    judgment: SessionJudgmentDTO


class ReportDTO(CustomBaseModel):
    period: ReportPeriodDTO
    active: ReportActiveDTO
    sounds: ReportSoundsDTO
    sessions: list[ReportSessionDTO]


class ReportResponse(BaseResponse):
    data: ReportDTO


class ReportParams(BaseRequest):
    period: ReportPeriodEnum
    start: date

from datetime import date, datetime
from typing import ClassVar
from uuid import UUID

from pydantic import Field

from app.enums import SessionActorEnum, SessionEventKindEnum, SessionPhaseEnum, SessionStatusEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, UploadRequest


class SessionStationDTO(CustomBaseModel):
    device_id: UUID


class SessionSettingsDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word_id"}

    word_id: UUID | None
    learning_enabled: bool
    version: int
    applied_version: int


class SessionProgressDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"current_phase", "phase_started_at", "last_heartbeat_at"}

    current_phase: SessionPhaseEnum | None
    phase_started_at: datetime | None
    last_heartbeat_at: datetime | None


class SessionPeriodDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"ended_at", "ended_by"}

    started_at: datetime
    ended_at: datetime | None
    ended_by: SessionActorEnum | None


class SessionDTO(CustomBaseModel):
    id: UUID
    status: SessionStatusEnum
    station: SessionStationDTO
    settings: SessionSettingsDTO
    progress: SessionProgressDTO
    period: SessionPeriodDTO


class SessionResponse(BaseResponse):
    data: SessionDTO


class SessionListResponse(BaseResponse):
    data: list[SessionDTO]


class StartSessionRequest(BaseRequest):
    null_fields: ClassVar[set] = {"word_id"}

    word_id: UUID | None = None
    learning_enabled: bool


class ChangeSessionWordRequest(BaseRequest):
    null_fields: ClassVar[set] = {"word_id"}

    word_id: UUID | None


class ChangeSessionLearningRequest(BaseRequest):
    enabled: bool


class HeartbeatSummaryRequest(BaseRequest):
    word_id: UUID
    local_date: date
    play_count: int = Field(..., ge=0)
    play_duration_ms: int = Field(..., ge=0)


class HeartbeatRequest(BaseRequest):
    null_fields: ClassVar[set] = {"current_phase", "phase_started_at"}

    current_phase: SessionPhaseEnum | None
    phase_started_at: datetime | None
    applied_settings_version: int = Field(..., ge=0)
    timezone: str = Field(..., min_length=1, max_length=64)
    summaries: list[HeartbeatSummaryRequest] = Field(default_factory=list, max_length=500)


class HeartbeatSessionDTO(CustomBaseModel):
    status: SessionStatusEnum
    settings: SessionSettingsDTO


class AcknowledgedSummaryDTO(CustomBaseModel):
    word_id: UUID
    local_date: date


class HeartbeatDTO(CustomBaseModel):
    session: HeartbeatSessionDTO
    acknowledged: list[AcknowledgedSummaryDTO]


class HeartbeatResponse(BaseResponse):
    data: HeartbeatDTO


class SessionEventRequest(BaseRequest):
    null_fields: ClassVar[set] = {"word_id"}

    kind: SessionEventKindEnum
    occurred_at: datetime
    word_id: UUID | None = None


class AddSessionEventsRequest(BaseRequest):
    events: list[SessionEventRequest] = Field(..., min_length=1, max_length=500)


class SessionEventWordDTO(CustomBaseModel):
    id: UUID


class SessionEventDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word"}

    id: UUID
    kind: SessionEventKindEnum
    occurred_at: datetime
    word: SessionEventWordDTO | None


class SessionEventListResponse(BaseResponse):
    data: list[SessionEventDTO]


class SessionSoundAudioDTO(CustomBaseModel):
    url: str


class SessionSoundJudgmentDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word_id"}

    word_id: UUID | None


class SessionSoundDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"judgment"}

    id: UUID
    session_id: UUID
    captured_at: datetime
    audio: SessionSoundAudioDTO
    judgment: SessionSoundJudgmentDTO | None


class SessionSoundUploadRequest(UploadRequest):
    captured_at: datetime


class SessionSoundListResponse(BaseResponse):
    data: list[SessionSoundDTO]

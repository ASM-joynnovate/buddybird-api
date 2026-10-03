from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.enums import JudgmentStatusEnum, SessionActorEnum, SessionEventKindEnum, SessionPhaseEnum, SessionStatusEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, FileDTO, PageParams, UploadRequest
from app.schemas.settings import SleepSettingsDTO, UpdateSleepSettingsRequest


class SessionStationDTO(CustomBaseModel):
    device_id: UUID


class SessionWordDTO(CustomBaseModel):
    id: UUID


class SessionScheduleDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"ends_at", "sleep"}

    ends_at: datetime | None
    sleep: SleepSettingsDTO | None


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


class SessionJudgmentDTO(CustomBaseModel):
    status: JudgmentStatusEnum


class SessionDTO(CustomBaseModel):
    id: UUID
    status: SessionStatusEnum
    station: SessionStationDTO
    word: SessionWordDTO
    schedule: SessionScheduleDTO
    progress: SessionProgressDTO
    period: SessionPeriodDTO
    judgment: SessionJudgmentDTO


class SessionResponse(BaseResponse):
    data: SessionDTO


class SessionListResponse(BaseResponse):
    data: list[SessionDTO]


class StartSessionRequest(BaseRequest):
    null_fields: ClassVar[set] = {"ends_at", "sleep"}

    word_id: UUID
    ends_at: AwareDatetime | None
    sleep: UpdateSleepSettingsRequest | None


class HeartbeatLearningSegmentRequest(BaseRequest):
    word_id: UUID
    started_at: AwareDatetime
    ended_at: AwareDatetime
    play_count: int = Field(..., ge=0)
    play_duration_ms: int = Field(..., ge=0)


class HeartbeatRequest(BaseRequest):
    null_fields: ClassVar[set] = {"current_phase", "phase_started_at"}

    current_phase: SessionPhaseEnum | None
    phase_started_at: datetime | None
    learning_segments: list[HeartbeatLearningSegmentRequest] = Field(default_factory=list, max_length=500)


class HeartbeatSessionDTO(CustomBaseModel):
    status: SessionStatusEnum


class AcknowledgedLearningSegmentDTO(CustomBaseModel):
    word_id: UUID
    started_at: datetime


class HeartbeatDTO(CustomBaseModel):
    session: HeartbeatSessionDTO
    acknowledged: list[AcknowledgedLearningSegmentDTO]


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


class SessionSoundJudgmentDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word_id"}

    word_id: UUID | None


class SessionSoundDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"judgment"}

    id: UUID
    session_id: UUID
    captured_at: datetime
    audio_file: FileDTO
    judgment: SessionSoundJudgmentDTO | None


class SessionSoundUploadRequest(UploadRequest):
    captured_at: datetime


class SessionSoundListParams(PageParams):
    mimicry: bool = False


class SessionSoundListResponse(BaseResponse):
    data: list[SessionSoundDTO]


class LearningDurationDTO(CustomBaseModel):
    duration_ms: int


class SessionSummaryWordDTO(CustomBaseModel):
    id: UUID
    name: str
    learning: LearningDurationDTO


class SessionSummarySessionDTO(CustomBaseModel):
    play_count: int
    learning: LearningDurationDTO


class SessionSummaryTotalDTO(CustomBaseModel):
    learning: LearningDurationDTO


class SessionSummaryDTO(CustomBaseModel):
    word: SessionSummaryWordDTO
    session: SessionSummarySessionDTO
    total: SessionSummaryTotalDTO


class SessionSummaryResponse(BaseResponse):
    data: SessionSummaryDTO

from datetime import datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import AwareDatetime, ConfigDict, Field

from app.enums import (
    JudgmentStatusEnum,
    SessionActorEnum,
    SessionEndReasonEnum,
    SessionEventKindEnum,
    SessionPhaseEnum,
    SessionStatusEnum,
)
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


class SessionSoundsDTO(CustomBaseModel):
    vad_count: int
    parrot_count: int
    mimic_count: int


class SessionDTO(CustomBaseModel):
    id: UUID
    status: SessionStatusEnum
    station: SessionStationDTO
    word: SessionWordDTO
    schedule: SessionScheduleDTO
    progress: SessionProgressDTO
    period: SessionPeriodDTO
    judgment: SessionJudgmentDTO
    sounds: SessionSoundsDTO


class SessionResponse(BaseResponse):
    data: SessionDTO


class SessionListResponse(BaseResponse):
    data: list[SessionDTO]


class BackofficeSessionWordDTO(CustomBaseModel):
    id: UUID
    name: str


class BackofficeSessionPeriodDTO(SessionPeriodDTO):
    allow_null_fields: ClassVar[set] = {"ended_at", "ended_by", "ended_reason"}

    ended_reason: SessionEndReasonEnum | None


class BackofficeSessionDisconnectionDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"ended_at"}

    started_at: datetime
    ended_at: datetime | None


class BackofficeSessionDTO(SessionDTO):
    word: BackofficeSessionWordDTO
    period: BackofficeSessionPeriodDTO
    disconnections: list[BackofficeSessionDisconnectionDTO]
    emergency_detections: list[datetime]


class BackofficeSessionListResponse(BaseResponse):
    data: list[BackofficeSessionDTO]


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

    kind: Literal[
        SessionEventKindEnum.SESSION_STARTED,
        SessionEventKindEnum.LEARNING_STARTED,
        SessionEventKindEnum.LEARNING_TOGGLED,
        SessionEventKindEnum.LEARNING_FINISHED,
        SessionEventKindEnum.WORD_CHANGED,
        SessionEventKindEnum.STATION_DISCONNECTED,
        SessionEventKindEnum.STATION_RECONNECTED,
        SessionEventKindEnum.SESSION_FINISHED,
    ]
    occurred_at: datetime
    word_id: UUID | None = None


class AddSessionEventsRequest(BaseRequest):
    events: list[SessionEventRequest] = Field(..., min_length=1, max_length=500)


class SessionEventWordDTO(CustomBaseModel):
    id: UUID


class SessionEventDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word", "ended_at"}

    id: UUID
    kind: SessionEventKindEnum
    occurred_at: datetime
    ended_at: datetime | None
    word: SessionEventWordDTO | None
    sound_ids: list[UUID]


class SessionEventListResponse(BaseResponse):
    data: list[SessionEventDTO]


class BackofficeSessionEventDTO(SessionEventDTO):
    allow_null_fields: ClassVar[set] = {"word", "ended_at", "is_learning"}

    word: BackofficeSessionWordDTO | None
    is_learning: bool | None


class BackofficeSessionEventListResponse(BaseResponse):
    data: list[BackofficeSessionEventDTO]


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
    model_config = ConfigDict(extra="ignore")

    mimic: bool = False


class SessionSoundListResponse(BaseResponse):
    data: list[SessionSoundDTO]


class BackofficeSessionSoundDTO(CustomBaseModel):
    id: UUID
    captured_at: datetime
    audio_file: FileDTO
    is_mimic: bool


class BackofficeSessionSoundListResponse(BaseResponse):
    data: list[BackofficeSessionSoundDTO]


class ActiveDurationDTO(CustomBaseModel):
    duration_ms: int


class SessionSummaryWordDTO(CustomBaseModel):
    id: UUID
    name: str
    active: ActiveDurationDTO


class SessionSummarySessionDTO(CustomBaseModel):
    play_count: int
    active: ActiveDurationDTO


class SessionSummaryTotalDTO(CustomBaseModel):
    active: ActiveDurationDTO


class SessionSummaryDTO(CustomBaseModel):
    word: SessionSummaryWordDTO
    session: SessionSummarySessionDTO
    total: SessionSummaryTotalDTO


class SessionSummaryResponse(BaseResponse):
    data: SessionSummaryDTO

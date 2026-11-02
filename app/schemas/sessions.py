from datetime import datetime
from typing import Annotated, ClassVar, Literal
from uuid import UUID

from pydantic import AwareDatetime, ConfigDict, Field, StringConstraints

from app.enums import (
    CorrectnessEnum,
    JudgmentStatusEnum,
    SessionActorEnum,
    SessionEndReasonEnum,
    SessionEventKindEnum,
    SessionLogKindEnum,
    SessionPhaseEnum,
    SessionSoundKindEnum,
    SessionSoundLabelTargetEnum,
    SessionStatusEnum,
)
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, FileDTO, PageParams, UploadDTO, UploadRequest
from app.schemas.settings import SleepSettingsDTO, UpdateSleepSettingsRequest

OperatorName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Memo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


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


class SessionEventsDTO(CustomBaseModel):
    distress_call_count: int
    parrot_disappeared_count: int


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
    events: SessionEventsDTO


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
    distress_call_detections: list[datetime]
    parrot_disappearances: list[datetime]


class BackofficeSessionListParams(PageParams):
    session_id: UUID | None = None
    label: list[CorrectnessEnum] | None = None


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


class SessionPetcamEventRequest(BaseRequest):
    kind: Literal[SessionEventKindEnum.PARROT_DISAPPEARED, SessionEventKindEnum.PARROT_APPEARED]
    occurred_at: datetime
    file_size: int = Field(gt=0)


class SessionPetcamEventUploadDTO(UploadDTO):
    event_id: UUID


class SessionPetcamEventUploadResponse(BaseResponse):
    data: SessionPetcamEventUploadDTO


class SessionPetcamVideoUploadRequest(BaseRequest):
    file_size: int = Field(gt=0)


class SessionUserReviewDTO(CustomBaseModel):
    is_correct: bool


class UpdateSessionUserReviewRequest(BaseRequest):
    is_correct: bool


class SessionEventDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word", "ended_at", "image", "video", "user_review"}

    id: UUID
    kind: SessionEventKindEnum
    occurred_at: datetime
    ended_at: datetime | None
    word: SessionEventWordDTO | None
    sound_ids: list[UUID]
    image: FileDTO | None
    video: FileDTO | None
    user_review: SessionUserReviewDTO | None


class SessionEventListResponse(BaseResponse):
    data: list[SessionEventDTO]


class BackofficeSessionEventUserReviewDTO(CustomBaseModel):
    is_correct: bool
    updated_at: datetime


class BackofficeSessionEventDTO(SessionEventDTO):
    allow_null_fields: ClassVar[set] = {
        "word",
        "ended_at",
        "image",
        "video",
        "user_review",
        "is_learning",
        "is_correct",
    }

    word: BackofficeSessionWordDTO | None
    user_review: BackofficeSessionEventUserReviewDTO | None
    is_learning: bool | None
    is_correct: bool | None


class BackofficeSessionEventListParams(BaseRequest):
    label: list[CorrectnessEnum] | None = None


class BackofficeSessionEventListResponse(BaseResponse):
    data: list[BackofficeSessionEventDTO]


class BackofficeSessionEventLabelDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"is_correct", "memo"}

    id: UUID
    is_correct: bool | None
    operator_name: str
    memo: str | None
    created_at: datetime


class BackofficeSessionEventDetailDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"is_correct", "user_review"}

    id: UUID
    kind: SessionEventKindEnum
    occurred_at: datetime
    is_correct: bool | None
    labels: list[BackofficeSessionEventLabelDTO]
    user_review: BackofficeSessionEventUserReviewDTO | None


class BackofficeSessionEventDetailResponse(BaseResponse):
    data: BackofficeSessionEventDetailDTO


class UpdateSessionEventLabelRequest(BaseRequest):
    null_fields: ClassVar[set] = {"memo"}

    is_correct: bool
    memo: Memo | None = None
    operator_name: OperatorName


class CancelSessionLabelRequest(BaseRequest):
    null_fields: ClassVar[set] = {"memo"}

    memo: Memo | None = None
    operator_name: OperatorName


class SessionSoundAnalysisDTO(CustomBaseModel):
    score: float


class SessionSoundJudgmentDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word_id"}

    word_id: UUID | None
    score: float


class SessionSoundDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"duration_ms", "analysis", "judgment", "user_review"}

    id: UUID
    session_id: UUID
    captured_at: datetime
    audio_file: FileDTO
    duration_ms: int | None
    analysis: SessionSoundAnalysisDTO | None
    judgment: SessionSoundJudgmentDTO | None
    user_review: SessionUserReviewDTO | None
    is_feed_shared: bool


class SessionSoundUploadRequest(UploadRequest):
    captured_at: datetime


class SessionSoundListResponse(BaseResponse):
    data: list[SessionSoundDTO]


class BackofficeSessionSoundUserReviewDTO(CustomBaseModel):
    is_correct: bool
    kind: SessionSoundKindEnum
    updated_at: datetime


class BackofficeSessionSoundDTO(SessionSoundDTO):
    allow_null_fields: ClassVar[set] = {
        "duration_ms",
        "analysis",
        "judgment",
        "user_review",
        "kind",
        "final_parrot_score",
        "final_mimic_score",
    }

    user_review: BackofficeSessionSoundUserReviewDTO | None
    kind: SessionSoundKindEnum | None
    final_parrot_score: float | None
    final_mimic_score: float | None
    is_labeled: bool


class BackofficeSessionSoundListParams(BaseRequest):
    kind: list[SessionSoundKindEnum] | None = None
    user_review: list[CorrectnessEnum] | None = None


class BackofficeSessionSoundListResponse(BaseResponse):
    data: list[BackofficeSessionSoundDTO]


class BackofficeParrotDetectionDTO(CustomBaseModel):
    model_version: str
    is_parrot: bool
    score: float
    call_count: int
    chirp_count: int
    analyzed_at: datetime


class BackofficeMimicJudgmentDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word_id"}

    model_version: str
    word_id: UUID | None
    score: float
    judged_at: datetime


class BackofficeSessionSoundLabelDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"is_positive", "score", "memo"}

    id: UUID
    target: SessionSoundLabelTargetEnum
    is_positive: bool | None
    score: float | None
    operator_name: str
    memo: str | None
    created_at: datetime


class BackofficeSessionSoundDetailDTO(BackofficeSessionSoundDTO):
    parrot_detections: list[BackofficeParrotDetectionDTO]
    mimic_judgments: list[BackofficeMimicJudgmentDTO]
    labels: list[BackofficeSessionSoundLabelDTO]


class BackofficeSessionSoundDetailResponse(BaseResponse):
    data: BackofficeSessionSoundDetailDTO


class UpdateSessionSoundLabelRequest(BaseRequest):
    null_fields: ClassVar[set] = {"memo"}

    is_positive: bool
    score: float = Field(..., ge=0, le=1)
    memo: Memo | None = None
    operator_name: OperatorName


class SessionLogListParams(PageParams):
    model_config = ConfigDict(extra="ignore")

    kind: list[SessionLogKindEnum] = Field(..., min_length=1)


class SessionLogSoundDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"duration_ms", "score", "user_review"}

    id: UUID
    occurred_at: datetime
    audio_file: FileDTO
    duration_ms: int | None
    score: float | None
    user_review: SessionUserReviewDTO | None


class SessionLogParrotDTO(SessionLogSoundDTO):
    kind: Literal[SessionLogKindEnum.PARROT]


class SessionLogMimicDTO(SessionLogSoundDTO):
    kind: Literal[SessionLogKindEnum.MIMIC]
    is_feed_shared: bool


class SessionLogDistressCallSoundDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"duration_ms"}

    id: UUID
    captured_at: datetime
    audio_file: FileDTO
    duration_ms: int | None


class SessionLogDistressCallDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"user_review"}

    id: UUID
    kind: Literal[SessionLogKindEnum.DISTRESS_CALL_DETECTED]
    occurred_at: datetime
    ended_at: datetime
    sounds: list[SessionLogDistressCallSoundDTO]
    user_review: SessionUserReviewDTO | None


class SessionLogParrotDisappearedDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"ended_at", "image", "video", "user_review"}

    id: UUID
    kind: Literal[SessionLogKindEnum.PARROT_DISAPPEARED]
    occurred_at: datetime
    ended_at: datetime | None
    image: FileDTO | None
    video: FileDTO | None
    user_review: SessionUserReviewDTO | None


class SessionLogParrotAppearedDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"image", "user_review"}

    id: UUID
    kind: Literal[SessionLogKindEnum.PARROT_APPEARED]
    occurred_at: datetime
    image: FileDTO | None
    user_review: SessionUserReviewDTO | None


SessionLogItemDTO = Annotated[
    SessionLogParrotDTO
    | SessionLogMimicDTO
    | SessionLogDistressCallDTO
    | SessionLogParrotDisappearedDTO
    | SessionLogParrotAppearedDTO,
    Field(discriminator="kind"),
]


class SessionLogListResponse(BaseResponse):
    data: list[SessionLogItemDTO]


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

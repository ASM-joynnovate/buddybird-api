from datetime import date, datetime
from typing import ClassVar, Literal
from uuid import UUID

from pydantic import Field

from app.enums import EmergencyNotificationEnum, PlatformEnum, SessionEventKindEnum, SessionStatusEnum
from app.schemas.base import BaseResponse, CustomBaseModel, FileDTO, PageParams
from app.schemas.sessions import SessionSoundAnalysisDTO
from app.schemas.users import BackofficeUserParrotDTO


class BackofficeEmergencySessionDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"ended_at"}

    id: UUID
    status: SessionStatusEnum
    started_at: datetime
    ended_at: datetime | None


class BackofficeEmergencyUserDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"nickname", "email", "photo_file"}

    id: UUID
    nickname: str | None
    email: str | None
    is_anonymous: bool
    is_deleted: bool
    photo_file: FileDTO | None


class BackofficeEmergencyDeviceDTO(CustomBaseModel):
    platform: str
    model: str
    app_version: str


class BackofficeEmergencySessionSoundDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"duration_ms", "analysis"}

    id: UUID
    captured_at: datetime
    audio_file: FileDTO
    duration_ms: int | None
    analysis: SessionSoundAnalysisDTO | None


class BackofficeEmergencySoundDTO(CustomBaseModel):
    sounds: list[BackofficeEmergencySessionSoundDTO]
    chirp_count: int


class BackofficeEmergencyNotificationDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"read_at"}

    sent_at: datetime
    read_at: datetime | None


class BackofficeEmergencyAppearedDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"image", "notification"}

    occurred_at: datetime
    image: FileDTO | None
    notification: BackofficeEmergencyNotificationDTO | None


class BackofficeEmergencyVisionDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"image", "video", "notification", "appeared"}

    image: FileDTO | None
    video: FileDTO | None
    notification: BackofficeEmergencyNotificationDTO | None
    appeared: BackofficeEmergencyAppearedDTO | None


class BackofficeEmergencyDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"ended_at", "parrot", "sound", "vision"}

    id: UUID
    kind: SessionEventKindEnum
    occurred_at: datetime
    ended_at: datetime | None
    session: BackofficeEmergencySessionDTO
    user: BackofficeEmergencyUserDTO
    parrot: BackofficeUserParrotDTO | None
    parrot_count: int
    device: BackofficeEmergencyDeviceDTO
    sound: BackofficeEmergencySoundDTO | None
    vision: BackofficeEmergencyVisionDTO | None


class BackofficeEmergencyListResponse(BaseResponse):
    data: list[BackofficeEmergencyDTO]


class BackofficeEmergencyListParams(PageParams):
    occurred_from: date | None = None
    occurred_to: date | None = None
    kind: Literal[SessionEventKindEnum.SOUND_EMERGENCY_DETECTED, SessionEventKindEnum.PARROT_DISAPPEARED] | None = None
    keyword: str | None = Field(None, min_length=1, max_length=100)
    user_id: UUID | None = None
    is_ongoing: bool | None = None
    notification: EmergencyNotificationEnum | None = None
    platform: PlatformEnum | None = None

from datetime import date, datetime
from typing import ClassVar
from uuid import UUID

from pydantic import model_validator

from app.enums import NotificationKindEnum, OAuthProviderEnum, SessionPhaseEnum, UserIssueEnum, UserLastSessionEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel, I18nDTO


class DashboardDailyCountDTO(CustomBaseModel):
    date: date
    count: int


class DashboardSessionsDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"average_duration_ms"}

    count: int
    previous_count: int
    duration_ms: int
    average_duration_ms: int | None
    daily: list[DashboardDailyCountDTO]


class DashboardUsersDTO(CustomBaseModel):
    total_count: int
    active_count: int
    signup_count: int
    previous_signup_count: int
    daily_signups: list[DashboardDailyCountDTO]


class DashboardWithdrawalsDTO(CustomBaseModel):
    count: int
    daily: list[DashboardDailyCountDTO]


class DashboardFeedbackDTO(CustomBaseModel):
    count: int
    previous_count: int


class DashboardNotificationKindDTO(CustomBaseModel):
    kind: NotificationKindEnum
    sent_count: int
    read_count: int


class DashboardNotificationDTO(CustomBaseModel):
    kind: NotificationKindEnum
    title: I18nDTO
    sent_at: datetime
    recipient_count: int
    read_count: int


class DashboardNotificationsDTO(CustomBaseModel):
    kinds: list[DashboardNotificationKindDTO]
    recent: list[DashboardNotificationDTO]
    scheduled: list[DashboardNotificationDTO]


class DashboardAnnouncementDTO(CustomBaseModel):
    id: UUID
    title: I18nDTO
    starts_at: datetime
    read_count: int


class DashboardDeviceVersionDTO(CustomBaseModel):
    app_version: str
    count: int


class DashboardDevicesDTO(CustomBaseModel):
    versions: list[DashboardDeviceVersionDTO]
    unsupported_count: int


class DashboardDTO(CustomBaseModel):
    sessions: DashboardSessionsDTO
    users: DashboardUsersDTO
    withdrawals: DashboardWithdrawalsDTO
    feedback: DashboardFeedbackDTO
    notifications: DashboardNotificationsDTO
    announcements: list[DashboardAnnouncementDTO]
    devices: DashboardDevicesDTO


class DashboardResponse(BaseResponse):
    data: DashboardDTO


class DashboardLivePhaseDTO(CustomBaseModel):
    phase: SessionPhaseEnum
    count: int


class DashboardLiveRunningDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"average_duration_ms"}

    count: int
    average_duration_ms: int | None
    phases: list[DashboardLivePhaseDTO]


class DashboardLiveHourlyDTO(CustomBaseModel):
    start: datetime
    count: int


class DashboardLiveTodayDTO(CustomBaseModel):
    started_count: int
    ended_count: int
    hourly: list[DashboardLiveHourlyDTO]


class DashboardLiveLast24HoursDTO(CustomBaseModel):
    heartbeat_expired_count: int
    emergency_detected_count: int
    judgment_failed_count: int


class DashboardLiveSessionsDTO(CustomBaseModel):
    running: DashboardLiveRunningDTO
    today: DashboardLiveTodayDTO
    last_24_hours: DashboardLiveLast24HoursDTO


class DashboardLiveWithdrawalsDTO(CustomBaseModel):
    failed_count: int


class DashboardLiveDTO(CustomBaseModel):
    generated_at: datetime
    sessions: DashboardLiveSessionsDTO
    withdrawals: DashboardLiveWithdrawalsDTO


class DashboardLiveResponse(BaseResponse):
    data: DashboardLiveDTO


class UserDashboardUsersDTO(CustomBaseModel):
    total_count: int
    signup_count: int
    previous_signup_count: int
    deleted_count: int


class UserDashboardWithdrawalsDTO(CustomBaseModel):
    count: int
    previous_count: int


class UserDashboardDailyDTO(CustomBaseModel):
    date: date
    total_count: int
    signup_count: int
    withdrawal_count: int
    running_user_count: int


class UserDashboardLastSessionDTO(CustomBaseModel):
    last_session: UserLastSessionEnum
    count: int


class UserDashboardIssueDTO(CustomBaseModel):
    issue: UserIssueEnum
    count: int


class UserDashboardProviderDTO(CustomBaseModel):
    provider: OAuthProviderEnum
    count: int


class UserDashboardAccountsDTO(CustomBaseModel):
    providers: list[UserDashboardProviderDTO]
    anonymous_count: int


class UserDashboardPlatformDTO(CustomBaseModel):
    platform: str
    count: int


class UserDashboardPushDTO(CustomBaseModel):
    pushable_count: int
    unpushable_count: int


class UserDashboardSpeciesDTO(CustomBaseModel):
    species: str
    count: int


class UserDashboardParrotsDTO(CustomBaseModel):
    total_count: int
    species: list[UserDashboardSpeciesDTO]


class UserDashboardDTO(CustomBaseModel):
    users: UserDashboardUsersDTO
    withdrawals: UserDashboardWithdrawalsDTO
    daily: list[UserDashboardDailyDTO]
    last_sessions: list[UserDashboardLastSessionDTO]
    issues: list[UserDashboardIssueDTO]
    accounts: UserDashboardAccountsDTO
    platforms: list[UserDashboardPlatformDTO]
    push: UserDashboardPushDTO
    parrots: UserDashboardParrotsDTO


class UserDashboardResponse(BaseResponse):
    data: UserDashboardDTO


class DashboardParams(BaseRequest):
    date_from: date
    date_to: date

    @model_validator(mode="after")
    def validate_period(self) -> DashboardParams:
        if not 0 <= (self.date_to - self.date_from).days < 180:
            raise ValueError("조회 기간은 1일 이상 180일 이하여야 합니다.")

        return self

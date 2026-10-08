from datetime import date, datetime
from typing import ClassVar
from uuid import UUID

from pydantic import model_validator

from app.enums import (
    NotificationKindEnum,
    OAuthProviderEnum,
    PlatformEnum,
    SessionPhaseEnum,
    UserIssueEnum,
    UserLastSessionEnum,
    WithdrawalSessionRangeEnum,
    WithdrawalUsagePeriodEnum,
)
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


class DashboardCountDTO(CustomBaseModel):
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
    feedback: DashboardCountDTO
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


class DashboardProviderDTO(CustomBaseModel):
    provider: OAuthProviderEnum
    count: int


class DashboardAccountsDTO(CustomBaseModel):
    providers: list[DashboardProviderDTO]
    anonymous_count: int


class DashboardPlatformDTO(CustomBaseModel):
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
    withdrawals: DashboardCountDTO
    daily: list[UserDashboardDailyDTO]
    last_sessions: list[UserDashboardLastSessionDTO]
    issues: list[UserDashboardIssueDTO]
    accounts: DashboardAccountsDTO
    platforms: list[DashboardPlatformDTO]
    push: UserDashboardPushDTO
    parrots: UserDashboardParrotsDTO


class UserDashboardResponse(BaseResponse):
    data: UserDashboardDTO


class FeedbackDashboardFeedbackDTO(CustomBaseModel):
    count: int
    previous_count: int
    writer_count: int


class FeedbackDashboardLocaleDTO(CustomBaseModel):
    locale: str
    count: int


class FeedbackDashboardDTO(CustomBaseModel):
    feedback: FeedbackDashboardFeedbackDTO
    daily: list[DashboardDailyCountDTO]
    app_versions: list[DashboardDeviceVersionDTO]
    platforms: list[DashboardPlatformDTO]
    locales: list[FeedbackDashboardLocaleDTO]


class FeedbackDashboardResponse(BaseResponse):
    data: FeedbackDashboardDTO


class WithdrawalDashboardUsagePeriodDTO(CustomBaseModel):
    usage_period: WithdrawalUsagePeriodEnum
    count: int


class WithdrawalDashboardSessionRangeDTO(CustomBaseModel):
    session_range: WithdrawalSessionRangeEnum
    count: int


class WithdrawalDashboardParrotsDTO(CustomBaseModel):
    registered_count: int
    unregistered_count: int


class WithdrawalDashboardErrorDTO(CustomBaseModel):
    error_code: str
    count: int


class WithdrawalDashboardDTO(CustomBaseModel):
    withdrawals: DashboardCountDTO
    signup_count: int
    daily: list[DashboardDailyCountDTO]
    accounts: DashboardAccountsDTO
    platforms: list[DashboardPlatformDTO]
    app_versions: list[DashboardDeviceVersionDTO]
    usage_periods: list[WithdrawalDashboardUsagePeriodDTO]
    session_ranges: list[WithdrawalDashboardSessionRangeDTO]
    parrots: WithdrawalDashboardParrotsDTO
    errors: list[WithdrawalDashboardErrorDTO]


class WithdrawalDashboardResponse(BaseResponse):
    data: WithdrawalDashboardDTO


class NotificationDashboardKindDTO(CustomBaseModel):
    kind: NotificationKindEnum
    sent_count: int
    read_count: int
    push_sent_count: int


class NotificationDashboardDailyDTO(CustomBaseModel):
    date: date
    report_count: int
    announcement_count: int
    marketing_count: int
    urgent_count: int


class NotificationDashboardDTO(CustomBaseModel):
    notifications: DashboardCountDTO
    kinds: list[NotificationDashboardKindDTO]
    daily: list[NotificationDashboardDailyDTO]


class NotificationDashboardResponse(BaseResponse):
    data: NotificationDashboardDTO


class AppUpdateDashboardDTO(CustomBaseModel):
    versions: list[DashboardDeviceVersionDTO]


class AppUpdateDashboardResponse(BaseResponse):
    data: AppUpdateDashboardDTO


class ConsentDashboardUsersDTO(CustomBaseModel):
    total_count: int


class ConsentDashboardDecisionsDTO(CustomBaseModel):
    granted_count: int
    denied_count: int
    waiting_count: int


class ConsentDashboardDailyDTO(CustomBaseModel):
    date: date
    granted_count: int
    denied_count: int


class ConsentDashboardVersionDTO(CustomBaseModel):
    version: int
    granted_count: int
    user_count: int


class ConsentDashboardPlatformDTO(CustomBaseModel):
    platform: str
    granted_count: int
    user_count: int


class ConsentDashboardLocaleDTO(CustomBaseModel):
    locale: str
    granted_count: int
    user_count: int


class ConsentDashboardDTO(CustomBaseModel):
    users: ConsentDashboardUsersDTO
    decisions: ConsentDashboardDecisionsDTO
    daily: list[ConsentDashboardDailyDTO]
    versions: list[ConsentDashboardVersionDTO]
    platforms: list[ConsentDashboardPlatformDTO]
    locales: list[ConsentDashboardLocaleDTO]


class ConsentDashboardResponse(BaseResponse):
    data: ConsentDashboardDTO


class DashboardParams(BaseRequest):
    date_from: date
    date_to: date

    @model_validator(mode="after")
    def validate_period(self) -> DashboardParams:
        if not 0 <= (self.date_to - self.date_from).days < 180:
            raise ValueError("조회 기간은 1일 이상 180일 이하여야 합니다.")

        return self


class AppUpdateDashboardParams(BaseRequest):
    platform: PlatformEnum

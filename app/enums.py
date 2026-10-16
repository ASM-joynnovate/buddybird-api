from enum import StrEnum


class OAuthProviderEnum(StrEnum):
    GOOGLE = "google"
    APPLE = "apple"
    KAKAO = "kakao"


class WithdrawalStatusEnum(StrEnum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    COMPLETED = "completed"
    UNCONFIRMED = "unconfirmed"


class ConsentStatusEnum(StrEnum):
    GRANTED = "granted"
    DENIED = "denied"


class PresetLanguageEnum(StrEnum):
    KO = "ko"
    EN = "en"
    JA = "ja"
    RU = "ru"
    ES = "es"


class SessionStatusEnum(StrEnum):
    RUNNING = "running"
    FINISHED = "finished"


class SessionPhaseEnum(StrEnum):
    LEARNING = "learning"
    REST = "rest"
    STRESS_CARE = "stress_care"
    SLEEPING = "sleeping"


class SessionActorEnum(StrEnum):
    USER = "user"
    SERVER = "server"


class SessionEndReasonEnum(StrEnum):
    USER = "user"
    SCHEDULED = "scheduled"
    HEARTBEAT_EXPIRED = "heartbeat_expired"
    LOGOUT = "logout"
    DEVICE_DELETED = "device_deleted"
    DEVICE_RELEASED = "device_released"


class NotificationKindEnum(StrEnum):
    ANNOUNCEMENT = "announcement"
    URGENT = "urgent"
    MARKETING = "marketing"
    REPORT = "report"
    EMERGENCY = "emergency"


class NotificationSettingKindEnum(StrEnum):
    ANNOUNCEMENT = "announcement"
    REPORT = "report"
    EMERGENCY = "emergency"
    MARKETING = "marketing"
    MARKETING_NIGHT = "marketing_night"


class NotificationDispatchTargetEnum(StrEnum):
    ALL = "all"
    SELECTED = "selected"


class NotificationDispatchStatusEnum(StrEnum):
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"


class SessionEventKindEnum(StrEnum):
    SESSION_STARTED = "session_started"
    LEARNING_STARTED = "learning_started"
    LEARNING_TOGGLED = "learning_toggled"
    LEARNING_FINISHED = "learning_finished"
    WORD_CHANGED = "word_changed"
    STATION_DISCONNECTED = "station_disconnected"
    STATION_RECONNECTED = "station_reconnected"
    DISTRESS_CALL_DETECTED = "distress_call_detected"
    PARROT_DISAPPEARED = "parrot_disappeared"
    PARROT_APPEARED = "parrot_appeared"
    SESSION_FINISHED = "session_finished"


class SessionEventFileKindEnum(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


class FileStatusEnum(StrEnum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    REJECTED = "rejected"


class JudgmentStatusEnum(StrEnum):
    PENDING = "pending"
    DONE = "done"


class SoundJudgmentStatusEnum(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class LocaleEnum(StrEnum):
    KO_KR = "ko-KR"
    EN_US = "en-US"
    JA_JP = "ja-JP"
    RU_RU = "ru-RU"
    ES_ES = "es-ES"


class PlatformEnum(StrEnum):
    IOS = "ios"
    ANDROID = "android"


class ReportPeriodEnum(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class UserLastSessionEnum(StrEnum):
    TODAY = "today"
    WITHIN_7_DAYS = "within_7_days"
    WITHIN_30_DAYS = "within_30_days"
    OVER_30_DAYS = "over_30_days"
    NONE = "none"


class UserIssueEnum(StrEnum):
    HEARTBEAT_EXPIRED = "heartbeat_expired"
    DISTRESS_CALL_DETECTED = "distress_call_detected"
    PARROT_DISAPPEARED = "parrot_disappeared"
    WITHDRAWAL_FAILED = "withdrawal_failed"


class EmergencyNotificationEnum(StrEnum):
    READ = "read"
    UNREAD = "unread"
    NONE = "none"


class SortOrderEnum(StrEnum):
    ASC = "asc"
    DESC = "desc"


class UserSortEnum(StrEnum):
    CREATED_AT = "created_at"
    RECENT_DURATION = "recent_duration"
    SESSION_COUNT = "session_count"
    STATUS = "status"
    APP_VERSION = "app_version"
    PARROT_COUNT = "parrot_count"


class WithdrawalProgressEnum(StrEnum):
    RUNNING = "running"
    RETRYING = "retrying"
    STOPPED = "stopped"
    COMPLETED = "completed"


class WithdrawalStepEnum(StrEnum):
    APPLE = "apple"
    GOOGLE = "google"
    KAKAO = "kakao"
    ACCOUNT = "account"


class WithdrawalStepStatusEnum(StrEnum):
    WAITING = "waiting"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"
    UNCONFIRMED = "unconfirmed"


class WithdrawalUsagePeriodEnum(StrEnum):
    SAME_DAY = "same_day"
    WITHIN_7_DAYS = "within_7_days"
    WITHIN_30_DAYS = "within_30_days"
    OVER_30_DAYS = "over_30_days"


class WithdrawalSessionRangeEnum(StrEnum):
    NONE = "none"
    ONE_TO_FOUR = "one_to_four"
    FIVE_OR_MORE = "five_or_more"


class WithdrawalSortEnum(StrEnum):
    CREATED_AT = "created_at"
    USAGE_PERIOD = "usage_period"
    SESSION_COUNT = "session_count"


class AnnouncementSortEnum(StrEnum):
    STARTS_AT = "starts_at"
    READ_COUNT = "read_count"


class StabilityIssueSortEnum(StrEnum):
    DATE = "date"
    NEW = "new"
    FREQ = "freq"
    USER = "user"


class StabilityEnvironmentEnum(StrEnum):
    PROD = "prod"
    DEV = "dev"
    LOCAL = "local"


class StabilityIssueLevelEnum(StrEnum):
    FATAL = "fatal"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class StabilityIssuePriorityEnum(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

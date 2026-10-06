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


class NotificationKindEnum(StrEnum):
    ANNOUNCEMENT = "announcement"
    URGENT = "urgent"
    MARKETING = "marketing"
    REPORT = "report"


class SessionEventKindEnum(StrEnum):
    SESSION_STARTED = "session_started"
    LEARNING_STARTED = "learning_started"
    LEARNING_TOGGLED = "learning_toggled"
    LEARNING_FINISHED = "learning_finished"
    WORD_CHANGED = "word_changed"
    STATION_DISCONNECTED = "station_disconnected"
    STATION_RECONNECTED = "station_reconnected"
    EMERGENCY_DETECTED = "emergency_detected"
    SESSION_FINISHED = "session_finished"


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


class PlatformEnum(StrEnum):
    IOS = "ios"
    ANDROID = "android"


class ReportPeriodEnum(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"

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


class ConsentKindEnum(StrEnum):
    AUDIO = "audio"
    VIDEO = "video"


class ConsentStatusEnum(StrEnum):
    GRANTED = "granted"
    DENIED = "denied"


class DeviceRoleEnum(StrEnum):
    STATION = "station"
    VIEWER = "viewer"


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
    STATION = "station"
    VIEWER = "viewer"
    SERVER = "server"


class NotificationKindEnum(StrEnum):
    EMERGENCY = "emergency"
    MIMICRY = "mimicry"
    STATION_DISCONNECT = "station_disconnect"
    DAILY_SUMMARY = "daily_summary"
    STREAK = "streak"


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

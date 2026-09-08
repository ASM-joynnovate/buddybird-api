from enum import StrEnum


class PhaseEnum(StrEnum):
    LEARNING = "LE"
    RESTING = "RE"


class LabelCategoryTargetEnum(StrEnum):
    CAPTURE = "CA"
    SEGMENT = "SE"

from enum import StrEnum


class PhaseEnum(StrEnum):
    LEARNING = "LE"
    RESTING = "RE"


class LabelStatusEnum(StrEnum):
    UNLABELED = "UL"
    LABELED = "LA"
    ALL = "AL"

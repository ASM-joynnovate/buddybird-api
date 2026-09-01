from enum import StrEnum


class OrderedStrEnum(StrEnum):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__order = len(self.__class__)

    def __ge__(self, other) -> bool:
        if self.__class__ is other.__class__:
            return self.__order >= other.__order
        return NotImplemented

    def __gt__(self, other) -> bool:
        if self.__class__ is other.__class__:
            return self.__order > other.__order
        return NotImplemented

    def __le__(self, other) -> bool:
        if self.__class__ is other.__class__:
            return self.__order <= other.__order
        return NotImplemented

    def __lt__(self, other) -> bool:
        if self.__class__ is other.__class__:
            return self.__order < other.__order
        return NotImplemented

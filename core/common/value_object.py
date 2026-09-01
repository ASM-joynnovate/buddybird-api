from enum import EnumMeta
from typing import Any, TypeVar

from core.common.errors import ValueObjectEnumError

ValueObjectType = TypeVar("ValueObjectType", bound="ValueObject")


class ValueObject:
    def __composite_values__(self) -> tuple[Any, ...]:
        return (self.value,)

    @classmethod
    def from_value(cls, value: Any) -> ValueObjectType:
        if isinstance(cls, EnumMeta):
            for item in cls:
                if item.value == value:
                    return item
            raise ValueObjectEnumError

        return cls(value=value)

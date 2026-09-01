from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, model_validator


class CustomBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_null_fields: ClassVar[set] = set()

    @model_validator(mode="before")
    @classmethod
    def process(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        return cls._process_dict(data)

    @classmethod
    def _process_dict(cls, data: dict) -> dict:
        res = {}
        for key, value in data.items():
            res[key] = cls._validate_and_transform_value(key, value)
        return res

    @classmethod
    def _validate_and_transform_value(cls, key: str, value: Any) -> Any:
        if value is None and not cls._is_null_allowed(key):
            raise ValueError(f"필드 '{key}'는 null일 수 없습니다.")
        return value

    @classmethod
    def _is_null_allowed(cls, key: str) -> bool:
        return key in cls.allow_null_fields or cls.allow_null_fields == {"*"}

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    null_fields: ClassVar[set[str]] = set()
    empty_str_fields: ClassVar[set[str]] = set()

    @model_validator(mode="before")
    @classmethod
    def process_empty_str_or_none(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        result = dict(data)

        for key, value in data.items():
            if value == "":
                if key in cls.empty_str_fields or "*" in cls.empty_str_fields:
                    continue

                if key in cls.null_fields or "*" in cls.null_fields:
                    result[key] = None
                    continue

                raise ValueError(f"필드 '{key}'는 빈 문자열일 수 없습니다.")

            if value is None and key not in cls.null_fields and "*" not in cls.null_fields:
                raise ValueError(f"필드 '{key}'는 null일 수 없습니다.")

        return result


class PageParams(BaseRequest):
    page: int = Field(1, ge=1)
    count_by_page: int = Field(12, ge=1, le=100)


class CustomBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allow_null_fields: ClassVar[set[str]] = set()

    @model_validator(mode="before")
    @classmethod
    def process(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for key, value in data.items():
                if value is None and key not in cls.allow_null_fields and "*" not in cls.allow_null_fields:
                    raise ValueError(f"필드 '{key}'는 null일 수 없습니다.")

        return data


class BaseResponse(BaseModel):
    message: str = ""
    data: Any = None
    meta: Any = None

from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, or_

from app.enums import CorrectnessEnum, LocaleEnum

SEOUL = ZoneInfo("Asia/Seoul")
MAX_PHOTO_BYTES = 5 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg", "image/png"}


def correctness_filter(column: ColumnElement, values: list[CorrectnessEnum]) -> ColumnElement[bool]:
    return or_(
        *(
            column.is_(None) if value == CorrectnessEnum.NONE else column.is_(value == CorrectnessEnum.CORRECT)
            for value in values
        )
    )


def resolve_locale(value: str | None) -> LocaleEnum:
    if value is None:
        return LocaleEnum.EN_US

    if value in LocaleEnum:
        return LocaleEnum(value)

    language = value.split("-")[0]

    for locale in LocaleEnum:
        if locale.split("-")[0] == language:
            return locale

    return LocaleEnum.EN_US

from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, or_

from app.enums import CorrectnessEnum

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


def capitalize_first(text: str) -> str:
    return text[:1].upper() + text[1:]

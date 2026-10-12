from zoneinfo import ZoneInfo

from app.enums import LocaleEnum

SEOUL = ZoneInfo("Asia/Seoul")


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

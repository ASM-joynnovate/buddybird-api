import json
from datetime import date, timedelta
from pathlib import Path

from app.config import config

LEGACY_DAILY_USERS = (
    {
        date.fromisoformat(row["date"]): row
        for row in json.loads((Path(__file__).parent / "daily_users.json").read_text())
    }
    if config.ENV == "prod"
    else {}
)


def get_legacy_user_counts(dates: list[date]) -> tuple[int, int, int]:
    signups = {day: row["signup_count"] for day, row in LEGACY_DAILY_USERS.items()}
    previous_dates = [day - timedelta(days=len(dates)) for day in dates]

    return (
        sum(signups.values()),
        sum(signups.get(day, 0) for day in dates),
        sum(signups.get(day, 0) for day in previous_dates),
    )

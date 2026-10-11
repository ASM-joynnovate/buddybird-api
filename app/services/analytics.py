import asyncio
import json
import logging
from functools import lru_cache

import httpx
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from app.config import config
from app.errors import DashboardSourceUnavailableError
from app.oauth.base import http_client
from app.schemas.dashboard import (
    AnalyticsDashboardDailyDTO,
    AnalyticsDashboardDTO,
    AnalyticsDashboardEventDTO,
    AnalyticsDashboardOnboardingDTO,
    DashboardDeviceVersionDTO,
    DashboardParams,
    DashboardPlatformDTO,
)
from app.services.dashboard import get_period

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_credentials() -> service_account.Credentials:
    return service_account.Credentials.from_service_account_info(
        json.loads(config.FIREBASE_SERVICE_ACCOUNT_JSON.get_secret_value()),
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )


async def get_dashboard(*, query: DashboardParams) -> AnalyticsDashboardDTO:
    if config.GA4_PROPERTY_ID is None or config.FIREBASE_SERVICE_ACCOUNT_JSON is None:
        raise DashboardSourceUnavailableError

    dates, *_ = get_period(query)
    date_ranges = [{"startDate": query.date_from.isoformat(), "endDate": query.date_to.isoformat()}]
    by_active_users = [{"metric": {"metricName": "activeUsers"}, "desc": True}]
    reports = [
        {
            "dimensions": [{"name": "date"}],
            "metrics": [{"name": "active1DayUsers"}, {"name": "active7DayUsers"}, {"name": "active28DayUsers"}],
        },
        {"dimensions": [{"name": "platform"}], "metrics": [{"name": "activeUsers"}], "orderBys": by_active_users},
        {"dimensions": [{"name": "appVersion"}], "metrics": [{"name": "activeUsers"}], "orderBys": by_active_users},
        {
            "dimensions": [{"name": "eventName"}],
            "metrics": [{"name": "eventCount"}, {"name": "totalUsers"}],
            "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}],
        },
        {
            "dimensions": [{"name": "eventName"}, {"name": "customEvent:step"}],
            "metrics": [{"name": "totalUsers"}],
            "dimensionFilter": {
                "filter": {
                    "fieldName": "eventName",
                    "inListFilter": {"values": ["onboarding_step_viewed", "onboarding_step_completed"]},
                }
            },
            "orderBys": [{"metric": {"metricName": "totalUsers"}, "desc": True}],
        },
    ]
    credentials = get_credentials()

    try:
        if not credentials.valid:
            await asyncio.to_thread(credentials.refresh, Request())

        response = await http_client.post(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{config.GA4_PROPERTY_ID}:batchRunReports",
            headers={"Authorization": f"Bearer {credentials.token}"},
            json={"requests": [{**report, "dateRanges": date_ranges} for report in reports]},
        )
    except (GoogleAuthError, httpx.HTTPError) as exc:
        logger.exception("GA4 조회 실패")

        raise DashboardSourceUnavailableError from exc

    if response.status_code != 200:
        logger.error("GA4 조회 실패: %s %s", response.status_code, response.text)

        raise DashboardSourceUnavailableError

    daily_rows, platform_rows, app_version_rows, event_rows, onboarding_rows = (
        [
            [value["value"] for value in row["dimensionValues"]]
            + [int(value["value"]) for value in row["metricValues"]]
            for row in report.get("rows", [])
        ]
        for report in response.json()["reports"]
    )

    daily_counts = {date_key: counts for date_key, *counts in daily_rows}
    daily = []

    for day in dates:
        dau, wau, mau = daily_counts.get(day.strftime("%Y%m%d"), (0, 0, 0))

        daily.append(AnalyticsDashboardDailyDTO(date=day, dau=dau, wau=wau, mau=mau))

    onboarding_counts: dict[str, dict[str, int]] = {}

    for event_name, step, count in onboarding_rows:
        onboarding_counts.setdefault(step, {})[event_name] = count

    return AnalyticsDashboardDTO(
        daily=daily,
        platforms=[DashboardPlatformDTO(platform=platform, count=count) for platform, count in platform_rows],
        app_versions=[
            DashboardDeviceVersionDTO(app_version=app_version, count=count) for app_version, count in app_version_rows
        ],
        events=[
            AnalyticsDashboardEventDTO(name=name, count=count, user_count=user_count)
            for name, count, user_count in event_rows
        ],
        onboarding=[
            AnalyticsDashboardOnboardingDTO(
                step=step,
                viewed_count=counts.get("onboarding_step_viewed", 0),
                completed_count=counts.get("onboarding_step_completed", 0),
            )
            for step, counts in onboarding_counts.items()
        ],
    )

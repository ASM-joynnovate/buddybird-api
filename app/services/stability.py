import asyncio
import logging
from datetime import datetime, time, timedelta

import httpx

from app.config import config
from app.errors import DashboardSourceUnavailableError
from app.oauth.base import http_client
from app.schemas.dashboard import (
    StabilityDashboardDTO,
    StabilityDashboardIssueDTO,
    StabilityDashboardParams,
    StabilityDashboardProjectDTO,
    StabilityDashboardReleaseDTO,
)

logger = logging.getLogger(__name__)


async def get_dashboard(*, query: StabilityDashboardParams) -> StabilityDashboardDTO:
    if config.SENTRY_API_TOKEN is None:
        raise DashboardSourceUnavailableError

    filters = {
        "start": datetime.combine(query.date_from, time(0)).isoformat(),
        "end": datetime.combine(query.date_to + timedelta(days=1), time(0)).isoformat(),
        "project": -1,
        "environment": {"prod": ["prod", "production"], "dev": ["dev", "development"]}.get(config.ENV, [config.ENV]),
    }
    requests = [
        ("projects", {}),
        (
            "sessions",
            {
                **filters,
                "field": ["crash_free_rate(user)", "crash_free_rate(session)"],
                "groupBy": "project",
                "interval": "1d",
                "includeSeries": 0,
            },
        ),
        (
            "sessions",
            {
                **filters,
                "field": ["crash_free_rate(user)", "count_unique(user)"],
                "groupBy": "release",
                "orderBy": "-count_unique(user)",
                "per_page": 10,
                "interval": "1d",
                "includeSeries": 0,
            },
        ),
        ("events", {**filters, "dataset": "errors", "field": ["project", "count()"]}),
        ("issues", {**filters, "sort": query.sort.value, "limit": 10}),
    ]

    try:
        responses = await asyncio.gather(
            *(
                http_client.get(
                    f"https://de.sentry.io/api/0/organizations/joynnovate/{path}/",
                    params=params,
                    headers={"Authorization": f"Bearer {config.SENTRY_API_TOKEN.get_secret_value()}"},
                )
                for path, params in requests
            )
        )
    except httpx.HTTPError as exc:
        logger.exception("Sentry 조회 실패")

        raise DashboardSourceUnavailableError from exc

    for response in responses:
        if response.status_code != 200:
            logger.error("Sentry 조회 실패: %s %s %s", response.url.path, response.status_code, response.text)

            raise DashboardSourceUnavailableError

    projects, project_sessions, release_sessions, error_events, issues = (response.json() for response in responses)

    session_totals = {str(group["by"]["project"]): group["totals"] for group in project_sessions["groups"]}
    error_counts = {row["project"]: row["count()"] for row in error_events["data"]}

    return StabilityDashboardDTO(
        projects=[
            StabilityDashboardProjectDTO(
                project=project["slug"],
                crash_free_user_rate=session_totals.get(project["id"], {}).get("crash_free_rate(user)"),
                crash_free_session_rate=session_totals.get(project["id"], {}).get("crash_free_rate(session)"),
                error_count=error_counts.get(project["slug"], 0),
            )
            for project in projects
        ],
        releases=[
            StabilityDashboardReleaseDTO(
                release=group["by"]["release"],
                crash_free_user_rate=group["totals"]["crash_free_rate(user)"],
                user_count=group["totals"]["count_unique(user)"],
            )
            for group in release_sessions["groups"]
        ],
        issues=[
            StabilityDashboardIssueDTO(
                project=issue["project"]["slug"],
                title=issue["title"],
                level=issue["level"],
                count=int(issue["count"]),
                user_count=issue["userCount"],
                first_seen=issue["firstSeen"],
                last_seen=issue["lastSeen"],
                url=issue["permalink"],
            )
            for issue in issues
        ],
    )

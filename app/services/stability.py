import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Any

import httpx

from app.config import config
from app.errors import DashboardSourceUnavailableError
from app.oauth.base import http_client
from app.schemas.dashboard import (
    StabilityDashboardDTO,
    StabilityDashboardIssueDTO,
    StabilityDashboardIssueReleaseDTO,
    StabilityDashboardParams,
    StabilityDashboardProjectDTO,
    StabilityDashboardReleaseDTO,
)

logger = logging.getLogger(__name__)


async def request(*, path: str, params: dict) -> Any:
    try:
        response = await http_client.get(
            f"https://de.sentry.io/api/0/organizations/joynnovate/{path}/",
            params=params,
            headers={"Authorization": f"Bearer {config.SENTRY_API_TOKEN.get_secret_value()}"},
        )
    except httpx.HTTPError as exc:
        logger.exception("Sentry 조회 실패")

        raise DashboardSourceUnavailableError from exc

    if response.status_code != 200:
        logger.error("Sentry 조회 실패: %s %s %s", response.url.path, response.status_code, response.text)

        raise DashboardSourceUnavailableError

    return response.json()


async def get_dashboard(*, query: StabilityDashboardParams) -> StabilityDashboardDTO:
    if config.SENTRY_API_TOKEN is None:
        raise DashboardSourceUnavailableError

    environments = {"prod": ["prod", "production"], "dev": ["dev", "development"]}
    filters = {
        "start": datetime.combine(query.date_from, time(0)).isoformat(),
        "end": datetime.combine(query.date_to + timedelta(days=1), time(0)).isoformat(),
        "project": -1,
        "environment": environments.get(config.ENV, [config.ENV]),
    }

    issue_environment = config.ENV if query.environment is None else query.environment.value
    issue_filters = {**filters, "environment": environments.get(issue_environment, [issue_environment])}
    issue_query = "is:unresolved"

    if query.release is not None:
        issue_query += f" release:{query.release}"

    if query.level is not None:
        issue_query += f" level:{query.level.value}"

    if query.priority is not None:
        issue_query += f" issue.priority:{query.priority.value}"

    if query.min_user_count is not None:
        issue_query += f" userCount:>={query.min_user_count}"

    if query.is_new is not None:
        issue_query += f" firstSeen:{'>=' if query.is_new else '<'}{filters['start']}"

    if query.is_unhandled is not None:
        issue_query += f" error.unhandled:{str(query.is_unhandled).lower()}"

    if query.is_regressed is not None:
        issue_query += " is:regressed" if query.is_regressed else " !is:regressed"

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
        (
            "events",
            {
                **issue_filters,
                "dataset": "errors",
                "field": ["project", "release", "count()"],
                "query": "has:release",
                "sort": "-count()",
                "per_page": 100,
            },
        ),
        (
            "issues",
            {
                **issue_filters,
                "project": -1 if query.project is None else query.project,
                "query": issue_query,
                "sort": query.sort.value,
                "limit": 10,
            },
        ),
    ]

    projects, project_sessions, release_sessions, error_events, release_events, issues = await asyncio.gather(
        *(request(path=path, params=params) for path, params in requests)
    )

    last_releases = {}

    if issues:
        issue_events = await request(
            path="events",
            params={
                **issue_filters,
                "dataset": "errors",
                "field": ["issue.id", "release", "last_seen()"],
                "query": f"has:release issue.id:[{','.join(issue['id'] for issue in issues)}]",
                "sort": "-last_seen()",
                "per_page": 100,
            },
        )

        last_releases = {str(row["issue.id"]): row["release"] for row in reversed(issue_events["data"])}

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
        issue_releases=[
            StabilityDashboardIssueReleaseDTO(project=row["project"], release=row["release"])
            for row in release_events["data"]
        ],
        issues=[
            StabilityDashboardIssueDTO(
                short_id=issue["shortId"],
                project=issue["project"]["slug"],
                title=issue["title"],
                culprit=issue["culprit"],
                level=issue["level"],
                substatus=issue["substatus"],
                is_unhandled=issue["isUnhandled"],
                release=last_releases.get(issue["id"]),
                count=int(issue["count"]),
                user_count=issue["userCount"],
                first_seen=issue["lifetime"]["firstSeen"],
                last_seen=issue["lastSeen"],
                url=issue["permalink"],
            )
            for issue in issues
        ],
    )

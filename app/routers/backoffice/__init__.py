from fastapi import APIRouter, Depends

from app.dependencies import require_backoffice
from app.routers.backoffice import (
    abuse_reports,
    announcements,
    app_updates,
    consents,
    dashboard,
    emergencies,
    feed,
    feedback,
    leaderboard,
    notifications,
    preset_words,
    sessions,
    users,
    withdrawals,
)

router = APIRouter(prefix="/backoffice", dependencies=[Depends(require_backoffice)], tags=["백오피스"])

for module in (
    abuse_reports,
    announcements,
    app_updates,
    consents,
    dashboard,
    emergencies,
    feed,
    feedback,
    leaderboard,
    notifications,
    preset_words,
    sessions,
    users,
    withdrawals,
):
    router.include_router(module.router)

from fastapi import APIRouter, Depends

from app.dependencies import require_backoffice
from app.routers.backoffice import (
    announcements,
    app_updates,
    consents,
    feedback,
    notifications,
    preset_words,
    users,
    withdrawals,
)

router = APIRouter(prefix="/backoffice", dependencies=[Depends(require_backoffice)], tags=["백오피스"])

for module in (announcements, app_updates, consents, feedback, notifications, preset_words, users, withdrawals):
    router.include_router(module.router)

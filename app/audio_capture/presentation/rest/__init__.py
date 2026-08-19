from fastapi import APIRouter

from .v1.backoffice_router import router as backoffice_v1_router
from .v1.router import router as audio_capture_v1_router

router = APIRouter()

router.include_router(audio_capture_v1_router, prefix="/v1/captures", tags=["오디오 클립"])
router.include_router(backoffice_v1_router, prefix="/v1/backoffice", tags=["백오피스"])

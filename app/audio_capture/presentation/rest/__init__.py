from fastapi import APIRouter

from .v1.router import router as audio_capture_v1_router

router = APIRouter()

router.include_router(audio_capture_v1_router, prefix="/v1/captures", tags=["오디오 클립"])

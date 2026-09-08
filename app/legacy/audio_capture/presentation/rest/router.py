from fastapi import APIRouter

from app.legacy.audio_capture.presentation.rest.v1.backoffice_router import router as backoffice_v1_router

router = APIRouter()

router.include_router(backoffice_v1_router, prefix="/v1/backoffice", tags=["백오피스"])

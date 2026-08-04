from fastapi import APIRouter
from scalar_fastapi import get_scalar_api_reference

from app.audio_capture.presentation.rest import router as audio_capture_router
from app.word.presentation.rest import router as word_router
from core.fastapi import ExtendedFastAPI


def register_routers(app: ExtendedFastAPI):
    api_router = APIRouter(prefix="/api")

    @api_router.get("/healthz", tags=["공통"])
    async def healthz():
        return {"status": "ok"}

    @api_router.get("/scalar", include_in_schema=False)
    async def scalar_html():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,  # Type: ignore
            title=app.title,  # Type: ignore
        )

    api_router.include_router(word_router)
    api_router.include_router(audio_capture_router)

    app.include_router(api_router)

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from scalar_fastapi import get_scalar_api_reference

from app.audio_capture.presentation.rest import router as audio_capture_router
from app.word.presentation.rest import router as word_router
from core.fastapi import ExtendedFastAPI


def register_routers(app: ExtendedFastAPI) -> None:
    api_router = APIRouter(prefix="/api")

    @api_router.get("/healthz", tags=["공통"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @api_router.get("/scalar", include_in_schema=False)
    async def scalar_html() -> HTMLResponse:
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,  # type: ignore
            title=app.title,  # type: ignore
        )

    api_router.include_router(word_router)
    api_router.include_router(audio_capture_router)

    app.include_router(api_router)

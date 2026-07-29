from fastapi import APIRouter

from .v1.router import router as word_v1_router

router = APIRouter()

router.include_router(word_v1_router, prefix="/v1/word", tags=["단어"])
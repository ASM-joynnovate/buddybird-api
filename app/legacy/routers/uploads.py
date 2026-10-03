from typing import Annotated

from fastapi import APIRouter, Form

from app.dependencies import DBSession, Storage
from app.legacy.schemas.captures import BatchCreateAudioCaptureRequest, BatchCreateAudioCaptureResponse
from app.legacy.services import captures
from app.schemas.base import BaseResponse

router = APIRouter()


@router.post("/captures", name="클립 배치 업로드", response_model=BatchCreateAudioCaptureResponse)
async def batch_create_audio_capture(
    body: Annotated[BatchCreateAudioCaptureRequest, Form(media_type="multipart/form-data")],
    db: DBSession,
    storage: Storage,
) -> BaseResponse:
    return BaseResponse(
        message="클립 업로드 성공",
        data=await captures.batch_create_audio_capture(data=body, db=db, storage=storage),
    )

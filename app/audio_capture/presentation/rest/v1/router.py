from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Form

from app.audio_capture.application.dto.audio_capture import BatchCreateAudioCaptureDTO
from app.audio_capture.application.use_cases.command.batch_create_audio_capture import BatchCreateAudioCaptureUseCase
from app.audio_capture.presentation.rest.v1.response.audio_capture import BatchCreateAudioCaptureResponse
from app.container import AppContainer
from core.common.response import BaseResponse

from .request import BatchCreateAudioCaptureRequest

router = APIRouter()


@router.post("", name="클립 배치 업로드", response_model=BatchCreateAudioCaptureResponse)
@inject
async def batch_create_audio_capture(
    body: Annotated[BatchCreateAudioCaptureRequest, Form(..., media_type="multipart/form-data")],
    use_case: BatchCreateAudioCaptureUseCase = Depends(
        Provide[AppContainer.audio_capture.batch_create_audio_capture_command]
    ),
):
    data = BatchCreateAudioCaptureDTO(
        **body.model_dump(exclude={"file", "metadata"}, exclude_unset=True),
        items=body.metadata,
        archive_file=await body.file.read(),
    )

    return BaseResponse(message="클립 업로드 성공", data=await use_case.execute(data=data))

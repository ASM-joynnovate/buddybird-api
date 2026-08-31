from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Form

from app.container import AppContainer
from app.shared_kernel.application.dto import CreateFileDTO
from app.word.application.dto import CreateWordDTO
from app.word.application.use_cases.command.create_word import CreateWordUseCase
from app.word.application.use_cases.query.get_word import GetWordUseCase
from app.word.presentation.rest.v1.request import CreateWordRequest
from app.word.presentation.rest.v1.response import GetWordResponse
from core.common.response import BaseResponse

router = APIRouter()


@router.get("/{word_id:uuid}", name="단어 조회", response_model=GetWordResponse)
@inject
async def get_by_id(
    word_id: UUID,
    use_case: Annotated[GetWordUseCase, Depends(Provide[AppContainer.word.get_word_query])],
) -> BaseResponse:
    return BaseResponse(message="단어 조회 성공", data=await use_case.execute(word_id=word_id))


@router.post("", name="단어 생성", response_model=BaseResponse)
@inject
async def create_word(
    body: Annotated[CreateWordRequest, Form(..., media_type="multipart/form-data")],
    use_case: Annotated[CreateWordUseCase, Depends(Provide[AppContainer.word.create_word_command])],
) -> BaseResponse:
    data = CreateWordDTO(
        **body.model_dump(exclude={"audio_file"}, exclude_unset=True),
        audio_file=CreateFileDTO(file=await body.audio_file.read(), name=body.audio_file.filename),
    )

    return BaseResponse(message="단어 업로드 성공", data=await use_case.execute(data=data))

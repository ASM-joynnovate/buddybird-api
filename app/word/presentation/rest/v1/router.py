from uuid import UUID
from typing import Annotated

from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends, Form

from app.container import AppContainer
from app.shared_kernel.application.dto.file import CreateFileDTO
from app.word.application.dto.word import CreateWordDTO
from app.word.application.use_cases.command.create_word import CreateWordUseCase
from app.word.application.use_cases.query.word import WordQueryUseCase
from core.common.response import BaseResponse
from app.word.presentation.rest.v1.response.word import GetWordResponse
from .request import CreateWordRequest

router = APIRouter()


@router.get(
    "/{word_id:uuid}",
    name="단어 조회 (ID)",
    response_model=GetWordResponse
)
@inject
async def get_by_id(
        word_id: UUID,
        use_case: WordQueryUseCase = Depends(
            Provide[AppContainer.word.word_query]
        )
):
    return BaseResponse(
        message="단어 조회 성공",
        data=await use_case.get_by_id(word_id=word_id)
    )

@router.post(
    "",
    name="단어 생성",
    response_model=BaseResponse
)
@inject
async def create_word(
        body: Annotated[CreateWordRequest, Form(..., media_type="multipart/form-data")],
        use_case: CreateWordUseCase = Depends(
            Provide[AppContainer.word.create_word_command]
        ),
):
    data = CreateWordDTO(
        **body.model_dump(exclude={"audio_file"}, exclude_unset=True),
        audio_file=CreateFileDTO(
            file=await body.audio_file.read(),
            name=body.audio_file.filename
        ),
    )

    return BaseResponse(
        message="단어 생성 성공",
        data=await use_case.execute(data=data)
    )
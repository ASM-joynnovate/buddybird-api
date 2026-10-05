from typing import Annotated

from fastapi import APIRouter, Depends, Form

from app.dependencies import DBSession, Storage, require_preset_word
from app.models import PresetWord
from app.schemas.base import BaseResponse
from app.schemas.preset_words import (
    CreatePresetWordRequest,
    PresetWordListResponse,
    PresetWordResponse,
    UpdatePresetWordRequest,
)
from app.services import preset_words

router = APIRouter(prefix="/preset-words")


@router.get("", name="단어 프리셋 목록 조회")
async def get_list(db: DBSession, storage: Storage) -> PresetWordListResponse:
    return PresetWordListResponse(
        message="단어 프리셋 목록 조회 성공", data=await preset_words.get_list(db=db, storage=storage)
    )


@router.post("", name="단어 프리셋 생성")
async def create(
    body: Annotated[CreatePresetWordRequest, Form(media_type="multipart/form-data")],
    db: DBSession,
    storage: Storage,
) -> PresetWordResponse:
    return PresetWordResponse(
        message="단어 프리셋 생성 성공", data=await preset_words.create(db=db, storage=storage, data=body)
    )


@router.patch("/{preset_word_id}", name="단어 프리셋 수정")
async def update(
    preset_word: Annotated[PresetWord, Depends(require_preset_word)],
    body: Annotated[UpdatePresetWordRequest, Form(media_type="multipart/form-data")],
    db: DBSession,
    storage: Storage,
) -> PresetWordResponse:
    return PresetWordResponse(
        message="단어 프리셋 수정 성공",
        data=await preset_words.update(db=db, storage=storage, preset_word=preset_word, data=body),
    )


@router.delete("/{preset_word_id}", name="단어 프리셋 삭제")
async def delete(preset_word: Annotated[PresetWord, Depends(require_preset_word)], db: DBSession) -> BaseResponse:
    await preset_words.delete(db=db, preset_word=preset_word)

    return BaseResponse(message="단어 프리셋 삭제 성공")

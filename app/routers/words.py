from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.dependencies import ActiveUser, DBSession, Storage, require_word
from app.models import Word
from app.schemas.base import BaseResponse, UploadRequest, UploadResponse
from app.schemas.words import SaveWordRequest, WordListResponse, WordResponse
from app.services import words

router = APIRouter(prefix="/words")


@router.post("", name="단어 등록", response_model=WordResponse)
async def create(user: ActiveUser, body: SaveWordRequest, db: DBSession, storage: Storage) -> WordResponse:
    return WordResponse(message="단어 등록 성공", data=await words.create(db=db, user=user, storage=storage, data=body))


@router.get("", name="단어 목록 조회", response_model=WordListResponse)
async def get_list(user: ActiveUser, db: DBSession, storage: Storage) -> WordListResponse:
    return WordListResponse(message="단어 목록 조회 성공", data=await words.get_list(db=db, user=user, storage=storage))


@router.get("/{word_id}", name="단어 상세 조회", response_model=WordResponse)
async def get_detail(word: Annotated[Word, Depends(require_word)], db: DBSession, storage: Storage) -> WordResponse:
    return WordResponse(message="단어 상세 조회 성공", data=await words.get_detail(db=db, storage=storage, word=word))


@router.patch("/{word_id}", name="단어 수정", response_model=WordResponse)
async def update(
    word: Annotated[Word, Depends(require_word)], body: SaveWordRequest, db: DBSession, storage: Storage
) -> WordResponse:
    return WordResponse(message="단어 수정 성공", data=await words.update(db=db, storage=storage, word=word, data=body))


@router.delete("/{word_id}", name="단어 삭제")
async def delete(word: Annotated[Word, Depends(require_word)], db: DBSession) -> BaseResponse:
    await words.delete(db=db, word=word)

    return BaseResponse(message="단어 삭제 성공")


@router.post("/{word_id}/recordings", name="녹음 샘플 업로드 URL 발급", response_model=UploadResponse)
async def add_recording(
    word: Annotated[Word, Depends(require_word)],
    body: UploadRequest,
    db: DBSession,
    storage: Storage,
) -> UploadResponse:
    return UploadResponse(
        message="녹음 샘플 업로드 URL 발급 성공",
        data=await words.add_recording(db=db, storage=storage, word=word, data=body),
    )


@router.delete("/{word_id}/recordings/{recording_id}", name="녹음 샘플 삭제")
async def delete_recording(
    word: Annotated[Word, Depends(require_word)], recording_id: UUID, db: DBSession
) -> BaseResponse:
    await words.delete_recording(db=db, word=word, recording_id=recording_id)

    return BaseResponse(message="녹음 샘플 삭제 성공")

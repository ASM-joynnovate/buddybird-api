from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.dependencies import ActiveUser, DBSession, Storage, require_parrot
from app.models import Parrot
from app.schemas.base import BaseResponse
from app.schemas.parrots import CreateParrotRequest, ParrotListResponse, ParrotResponse, UpdateParrotRequest
from app.services import parrots

router = APIRouter(prefix="/parrots")


@router.post("", name="앵무새 등록", response_model=ParrotResponse)
async def create(user: ActiveUser, body: CreateParrotRequest, db: DBSession, storage: Storage) -> ParrotResponse:
    return ParrotResponse(
        message="앵무새 등록 성공", data=await parrots.create(db=db, user=user, storage=storage, data=body)
    )


@router.get("", name="앵무새 목록 조회", response_model=ParrotListResponse)
async def get_list(user: ActiveUser, db: DBSession, storage: Storage) -> ParrotListResponse:
    return ParrotListResponse(
        message="앵무새 목록 조회 성공", data=await parrots.get_list(db=db, user=user, storage=storage)
    )


@router.get("/{parrot_id}", name="앵무새 상세 조회", response_model=ParrotResponse)
async def get_detail(parrot: Annotated[Parrot, Depends(require_parrot)], storage: Storage) -> ParrotResponse:
    return ParrotResponse(message="앵무새 상세 조회 성공", data=parrots.get_detail(parrot=parrot, storage=storage))


@router.patch("/{parrot_id}", name="앵무새 수정", response_model=ParrotResponse)
async def update(
    parrot: Annotated[Parrot, Depends(require_parrot)], body: UpdateParrotRequest, db: DBSession, storage: Storage
) -> ParrotResponse:
    return ParrotResponse(
        message="앵무새 수정 성공", data=await parrots.update(db=db, storage=storage, parrot=parrot, data=body)
    )


@router.delete("/{parrot_id}", name="앵무새 삭제")
async def delete(parrot: Annotated[Parrot, Depends(require_parrot)], db: DBSession) -> BaseResponse:
    await parrots.delete(db=db, parrot=parrot)

    return BaseResponse(message="앵무새 삭제 성공")


@router.put("/{parrot_id}/photo", name="앵무새 사진 수정", response_model=ParrotResponse)
async def update_photo(
    parrot: Annotated[Parrot, Depends(require_parrot)],
    file: Annotated[UploadFile, File(description="앵무새 사진")],
    db: DBSession,
    storage: Storage,
) -> ParrotResponse:
    return ParrotResponse(
        message="앵무새 사진 수정 성공",
        data=await parrots.update_photo(db=db, storage=storage, parrot=parrot, file=file),
    )


@router.delete("/{parrot_id}/photo", name="앵무새 사진 삭제")
async def delete_photo(parrot: Annotated[Parrot, Depends(require_parrot)], db: DBSession) -> BaseResponse:
    await parrots.delete_photo(db=db, parrot=parrot)

    return BaseResponse(message="앵무새 사진 삭제 성공")

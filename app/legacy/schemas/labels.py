from uuid import UUID

from pydantic import Field
from pydantic.experimental.missing_sentinel import MISSING

from app.legacy.models import LabelCategoryTargetEnum
from app.schemas.base import BaseRequest, BaseResponse, CustomBaseModel


class CreateLabelCategoryRequest(BaseRequest):
    name: str = Field(..., min_length=1, max_length=100, description="카테고리명", examples=["새 소리"])
    display_order: int = Field(0, description="노출 순서", examples=[0])
    target: LabelCategoryTargetEnum = Field(
        LabelCategoryTargetEnum.SEGMENT, description="라벨 적용 대상", examples=[LabelCategoryTargetEnum.SEGMENT]
    )


class UpdateLabelCategoryRequest(BaseRequest):
    name: str | MISSING = Field(MISSING, min_length=1, max_length=100, description="카테고리명", examples=["새 소리"])
    display_order: int | MISSING = Field(MISSING, description="노출 순서", examples=[0])


class CreateLabelOptionRequest(BaseRequest):
    name: str = Field(..., min_length=1, max_length=100, description="옵션명", examples=["짹짹"])
    display_order: int = Field(0, description="노출 순서", examples=[0])


class UpdateLabelOptionRequest(BaseRequest):
    name: str | MISSING = Field(MISSING, min_length=1, max_length=100, description="옵션명", examples=["짹짹"])
    display_order: int | MISSING = Field(MISSING, description="노출 순서", examples=[0])


class GetLabelOptionDTO(CustomBaseModel):
    id: UUID = Field(..., description="옵션 ID")
    name: str = Field(..., description="옵션명")
    display_order: int = Field(..., description="노출 순서")


class GetLabelCategoryDTO(CustomBaseModel):
    id: UUID = Field(..., description="카테고리 ID")
    name: str = Field(..., description="카테고리명")
    display_order: int = Field(..., description="노출 순서")
    target: LabelCategoryTargetEnum = Field(..., description="라벨 적용 대상")
    options: list[GetLabelOptionDTO] = Field(..., description="하위 옵션 목록")


class GetLabelListResponse(BaseResponse):
    data: list[GetLabelCategoryDTO]

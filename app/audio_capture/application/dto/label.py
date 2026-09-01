from uuid import UUID

from pydantic import Field

from app.audio_capture.domain.enums import LabelCategoryTargetEnum
from core.common import CustomBaseModel
from core.common.sentinel import MISSING


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


class CreateLabelCategoryDTO(CustomBaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="카테고리명")
    display_order: int = Field(0, description="노출 순서")
    target: LabelCategoryTargetEnum = Field(LabelCategoryTargetEnum.SEGMENT, description="라벨 적용 대상")


class UpdateLabelCategoryDTO(CustomBaseModel):
    name: str | MISSING = Field(MISSING, min_length=1, max_length=100, description="카테고리명")
    display_order: int | MISSING = Field(MISSING, description="노출 순서")


class CreateLabelOptionDTO(CustomBaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="옵션명")
    display_order: int = Field(0, description="노출 순서")


class UpdateLabelOptionDTO(CustomBaseModel):
    name: str | MISSING = Field(MISSING, min_length=1, max_length=100, description="옵션명")
    display_order: int | MISSING = Field(MISSING, description="노출 순서")

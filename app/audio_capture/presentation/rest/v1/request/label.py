from pydantic import Field

from app.audio_capture.domain.enums import LabelCategoryTargetEnum
from core.common.request import BaseRequest
from core.common.sentinel import MISSING


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

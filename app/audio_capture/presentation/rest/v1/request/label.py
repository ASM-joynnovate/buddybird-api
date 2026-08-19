from pydantic import BaseModel, ConfigDict, Field


class CreateLabelCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100, description="카테고리명", examples=["새 소리"])
    display_order: int = Field(0, description="노출 순서", examples=[0])


class UpdateLabelCategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=100, description="카테고리명", examples=["새 소리"])
    display_order: int | None = Field(None, description="노출 순서", examples=[0])


class CreateLabelOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100, description="옵션명", examples=["짹짹"])
    display_order: int = Field(0, description="노출 순서", examples=[0])


class UpdateLabelOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, min_length=1, max_length=100, description="옵션명", examples=["짹짹"])
    display_order: int | None = Field(None, description="노출 순서", examples=[0])

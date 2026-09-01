from pydantic import Field, computed_field

from core.common import CustomBaseModel


class GetFileDTO(CustomBaseModel):
    name: str = Field(..., description="이름", validation_alias="file_name")
    path: str = Field(..., description="경로", validation_alias="file_path")
    content_type: str = Field(..., description="MIME 타입", validation_alias="file_type")

    @computed_field
    @property
    def full_path(self) -> str:
        return f"{self.path}/{self.name}"


class CreateFileDTO(CustomBaseModel):
    name: str = Field(..., description="파일 이름")
    file: bytes = Field(..., description="파일 데이터")

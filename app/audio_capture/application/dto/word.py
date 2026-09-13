from typing import ClassVar
from uuid import UUID

from pydantic import Field

from core.common import CustomBaseModel


class GetWordSummaryDTO(CustomBaseModel):
    id: UUID = Field(..., description="ID")
    label: str = Field(..., description="단어명")


class GetWordDTO(GetWordSummaryDTO):
    allow_null_fields: ClassVar[set] = {"firebase_anon_uid", "device_platform", "device_os_version", "device_model"}

    firebase_anon_uid: str | None = Field(None, max_length=128, description="Firebase Authentication 익명 ID")
    client_word_id: str = Field(..., description="클라이언트 단어 ID")
    device_platform: str | None = Field(None, description="단어를 녹음한 기기의 OS")
    device_os_version: str | None = Field(None, description="단어를 녹음한 기기의 OS 버전")
    device_model: str | None = Field(None, description="단어를 녹음한 기기의 모델명")

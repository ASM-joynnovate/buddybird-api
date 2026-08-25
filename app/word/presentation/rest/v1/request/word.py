from typing import Annotated

from fastapi import File, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.word.presentation.rest.v1.errors import ReservedClientWordIdError


class CreateWordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., description="단어명", examples=["안녕"])
    firebase_anon_uid: str = Field(
        ..., description="Firebase Authentication UID", examples=["FJTNzziLv9VlWUaOMUUdrWNe3Rm2"]
    )
    client_word_id: str = Field(..., description="클라이언트에서 사용하는 단어의 ID", examples=["preset-apple"])
    audio_file: Annotated[UploadFile, File(..., description="단어 오디오 파일")]
    device_platform: str | None = Field(None, max_length=10, description="단어를 녹음한 기기의 OS")
    device_os_version: str | None = Field(None, max_length=20, description="단어를 녹음한 기기의 OS 버전")
    device_model: str | None = Field(None, max_length=30, description="단어를 녹음한 기기의 모델명")

    # TODO: API 호출 및 도메인 로직에서 device_platform이 `iOS`, `Android` 만 들어가도록 하는 기능 추가 필요

    @field_validator("client_word_id")
    @classmethod
    def not_reserved(cls, value: str) -> str:
        if value.startswith("preset"):
            raise ReservedClientWordIdError
        return value

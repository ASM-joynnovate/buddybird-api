from typing import Annotated

from fastapi import File, UploadFile
from pydantic import BaseModel, ConfigDict, Field


class CreateWordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., description="단어명", examples=["안녕"])
    firebase_anon_uid: str = Field(
        ..., description="Firebase Authentication UID", examples=["FJTNzziLv9VlWUaOMUUdrWNe3Rm2"]
    )
    client_word_id: str = Field(..., description="클라이언트에서 사용하는 단어의 ID", examples=["0001"])
    audio_file: Annotated[UploadFile, File(..., description="단어 오디오 파일")]
    device_platform: str | None = Field(None, max_length=200, description="단어를 녹음한 기기의 OS")
    device_os_version: str | None = Field(None, max_length=200, description="단어를 녹음한 기기의 OS 버전")
    device_model: str | None = Field(None, max_length=200, description="단어를 녹음한 기기의 모델명")

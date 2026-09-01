from typing import Annotated, ClassVar

from fastapi import File, UploadFile
from pydantic import Field, field_validator

from core.common.request import BaseRequest


class CreateWordRequest(BaseRequest):
    null_fields: ClassVar[set] = {"device_platform", "device_os_version", "device_model"}

    label: str = Field(..., min_length=1, max_length=100, description="단어명", examples=["안녕"])
    firebase_anon_uid: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Firebase Authentication UID",
        examples=["FJTNzziLv9VlWUaOMUUdrWNe3Rm2"],
    )
    client_word_id: str = Field(..., description="클라이언트에서 사용하는 단어의 ID", examples=["custom-apple"])
    audio_file: Annotated[UploadFile, File(..., description="단어 오디오 파일", examples=["word.wav"])]
    device_platform: str | None = Field(None, max_length=10, description="단어를 녹음한 기기의 OS", examples=["iOS"])
    device_os_version: str | None = Field(
        None, max_length=20, description="단어를 녹음한 기기의 OS 버전", examples=["18.6"]
    )
    device_model: str | None = Field(
        None, max_length=30, description="단어를 녹음한 기기의 모델명", examples=["iPhone 16"]
    )

    # TODO: API 호출 및 도메인 로직에서 device_platform이 `iOS`, `Android` 만 들어가도록 하는 기능 추가 필요

    @field_validator("client_word_id")
    @classmethod
    def not_reserved(cls, value: str) -> str:
        if value.startswith("preset"):
            raise ValueError("preset으로 시작하는 값은 사용할 수 없습니다")
        return value

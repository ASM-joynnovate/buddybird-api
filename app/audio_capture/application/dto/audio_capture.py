from datetime import date, datetime
from typing import ClassVar, Literal

from pydantic import Field

from app.audio_capture.domain.enum import PhaseEnum
from core.common import CustomBaseModel


class CreateAudioCaptureItemDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"app_version", "parrot_species", "parrot_birthdate"}

    client_capture_id: str = Field(..., max_length=50, description="클라이언트가 부여한 클립 ID")
    client_session_id: str = Field(..., max_length=30, description="클립을 캡처한 세션 ID")
    client_word_id: str = Field(..., max_length=50, description="클립이 가리키는 단어의 클라이언트 ID")
    cycle: int = Field(..., description="세션의 사이클 번호")
    phase: PhaseEnum = Field(..., description="클립을 캡처한 세션 구간")
    captured_at: datetime = Field(..., description="클라이언트에서 클립을 캡처한 시각")
    file_name: str = Field(..., max_length=255, description="압축 파일 안에서 이 클립의 오디오를 가리키는 이름")
    app_version: str | None = Field(None, max_length=12, description="클립을 캡처한 앱 버전")
    parrot_species: str | None = Field(None, max_length=50, description="앵무새 종")
    parrot_birthdate: date | None = Field(None, description="앵무새 생년월일")


class BatchCreateAudioCaptureDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"device_platform", "device_os_version", "device_model"}

    firebase_anon_uid: str = Field(..., max_length=30, description="Firebase Authentication 익명 ID")
    items: list[CreateAudioCaptureItemDTO] = Field(..., description="개별 클립 메타데이터")
    archive_file: bytes = Field(..., description="클립 오디오를 담은 압축 파일")
    device_platform: str | None = Field(None, max_length=10, description="클립을 캡처한 기기의 OS")
    device_os_version: str | None = Field(None, max_length=20, description="클립을 캡처한 기기의 OS 버전")
    device_model: str | None = Field(None, max_length=30, description="클립을 캡처한 기기의 모델명")


class AudioCaptureUploadResultDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"code", "error_code", "message"}

    status: Literal["success", "rejected"] = Field(..., description="항목의 저장 결과")
    code: int | None = Field(None, description="거부된 항목의 HTTP 상태 코드")
    error_code: str | None = Field(None, description="거부된 항목의 에러 코드")
    message: str | None = Field(None, description="거부된 항목의 에러 메시지")

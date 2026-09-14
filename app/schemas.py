import re
import unicodedata
from datetime import date, datetime
from typing import Any, ClassVar, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.models import LabelCategoryTargetEnum, PhaseEnum

CATEGORY_NAME_DESCRIPTION = "카테고리명"
DISPLAY_ORDER_DESCRIPTION = "노출 순서"
START_MS_DESCRIPTION = "원본 파일 기준 시작 위치 ms"
END_MS_DESCRIPTION = "원본 파일 기준 끝 위치 ms"


class BaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    null_fields: ClassVar[set[str]] = set()
    empty_str_fields: ClassVar[set[str]] = set()

    @model_validator(mode="before")
    @classmethod
    def process_empty_str_or_none(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        result = dict(data)

        for key, value in data.items():
            if value == "":
                if key in cls.empty_str_fields or "*" in cls.empty_str_fields:
                    continue

                if key in cls.null_fields or "*" in cls.null_fields:
                    result[key] = None
                    continue

                raise ValueError(f"필드 '{key}'는 빈 문자열일 수 없습니다.")

            if value is None and key not in cls.null_fields and "*" not in cls.null_fields:
                raise ValueError(f"필드 '{key}'는 null일 수 없습니다.")

        return result


class CustomBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allow_null_fields: ClassVar[set[str]] = set()

    @model_validator(mode="before")
    @classmethod
    def process(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for key, value in data.items():
                if value is None and key not in cls.allow_null_fields and "*" not in cls.allow_null_fields:
                    raise ValueError(f"필드 '{key}'는 null일 수 없습니다.")

        return data


class PageParams(BaseRequest):
    page: int = Field(1, description="페이지 번호", ge=1, examples=[1])
    count_by_page: int = Field(12, description="페이지 당 조회 개수", ge=1, le=100, examples=[10])


class BaseResponse(BaseModel):
    message: str = ""
    data: Any = None
    meta: Any = None


class CreateLabelCategoryRequest(BaseRequest):
    name: str = Field(..., min_length=1, max_length=100, description=CATEGORY_NAME_DESCRIPTION, examples=["새 소리"])
    display_order: int = Field(0, description=DISPLAY_ORDER_DESCRIPTION, examples=[0])
    target: LabelCategoryTargetEnum = Field(
        LabelCategoryTargetEnum.SEGMENT, description="라벨 적용 대상", examples=[LabelCategoryTargetEnum.SEGMENT]
    )


class UpdateLabelCategoryRequest(BaseRequest):
    name: str | MISSING = Field(
        MISSING, min_length=1, max_length=100, description=CATEGORY_NAME_DESCRIPTION, examples=["새 소리"]
    )
    display_order: int | MISSING = Field(MISSING, description=DISPLAY_ORDER_DESCRIPTION, examples=[0])


class CreateLabelOptionRequest(BaseRequest):
    name: str = Field(..., min_length=1, max_length=100, description="옵션명", examples=["짹짹"])
    display_order: int = Field(0, description=DISPLAY_ORDER_DESCRIPTION, examples=[0])


class UpdateLabelOptionRequest(BaseRequest):
    name: str | MISSING = Field(MISSING, min_length=1, max_length=100, description="옵션명", examples=["짹짹"])
    display_order: int | MISSING = Field(MISSING, description=DISPLAY_ORDER_DESCRIPTION, examples=[0])


class GetLabelOptionDTO(CustomBaseModel):
    id: UUID = Field(..., description="옵션 ID")
    name: str = Field(..., description="옵션명")
    display_order: int = Field(..., description=DISPLAY_ORDER_DESCRIPTION)


class GetLabelCategoryDTO(CustomBaseModel):
    id: UUID = Field(..., description="카테고리 ID")
    name: str = Field(..., description=CATEGORY_NAME_DESCRIPTION)
    display_order: int = Field(..., description=DISPLAY_ORDER_DESCRIPTION)
    target: LabelCategoryTargetEnum = Field(..., description="라벨 적용 대상")
    options: list[GetLabelOptionDTO] = Field(..., description="하위 옵션 목록")


class CreateAudioSegmentRequest(BaseRequest):
    start_ms: int = Field(..., ge=0, description=START_MS_DESCRIPTION, examples=[0])
    end_ms: int = Field(..., ge=0, description=END_MS_DESCRIPTION, examples=[1000])


class TrimAudioSegmentRequest(BaseRequest):
    start_ms: int = Field(..., ge=0, description=START_MS_DESCRIPTION, examples=[0])
    end_ms: int = Field(..., ge=0, description=END_MS_DESCRIPTION, examples=[1000])


class AssignAudioSegmentLabelRequest(BaseRequest):
    label_option_id: UUID = Field(
        ...,
        description="지정할 라벨 옵션 ID",
        examples=["0198f4b0-68c0-7000-8000-000000000001"],
    )


class UpdateAudioSegmentMemoRequest(BaseRequest):
    null_fields: ClassVar[set] = {"memo"}

    memo: str | None = Field(..., description="메모. null이면 메모를 지운다", examples=["소리가 선명함"])


class GetAudioSegmentDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"label_option_id", "memo"}

    id: UUID = Field(..., description="세그먼트 ID")
    start_ms: int = Field(..., description=START_MS_DESCRIPTION)
    end_ms: int = Field(..., description=END_MS_DESCRIPTION)
    label_option_id: UUID | None = Field(None, description="지정된 라벨 옵션 ID")
    memo: str | None = Field(None, description="메모")
    audio_url: str = Field(..., description="세그먼트 오디오 URL")


class GetAudioCaptureListRequest(PageParams):
    null_fields: ClassVar[set] = {
        "firebase_anon_uid",
        "word_label",
        "parrot_species",
        "device_model",
        "device_platform",
        "device_os_version",
        "label_option_ids",
        "has_memo",
        "date_from",
        "date_to",
    }

    firebase_anon_uid: str | None = Field(
        None,
        max_length=128,
        description="Firebase Authentication 익명 ID",
        examples=["FJTNzziLv9VlWUaOMUUdrWNe3Rm2"],
    )
    word_label: str | None = Field(None, description="연결된 단어명", examples=["안녕"])
    parrot_species: str | None = Field(
        None, max_length=50, description="앵무새 종 완전일치 필터", examples=["왕관앵무"]
    )
    device_model: str | None = Field(
        None, max_length=30, description="클립을 캡처한 기기 모델 완전일치 필터", examples=["iPhone 16"]
    )
    device_platform: str | None = Field(
        None, max_length=10, description="클립을 캡처한 기기 OS 완전일치 필터", examples=["iOS"]
    )
    device_os_version: str | None = Field(
        None, max_length=20, description="클립을 캡처한 기기 OS 버전 완전일치 필터", examples=["18.6"]
    )
    label_option_ids: list[UUID] | None = Field(None, description="클립 라벨 옵션 ID 필터", examples=[[]])
    has_memo: bool | None = Field(None, description="메모가 있는 세그먼트 존재 여부 필터", examples=[True])
    date_from: datetime | None = Field(None, description="캡처 시각 시작 범위", examples=["2026-08-01T00:00:00Z"])
    date_to: datetime | None = Field(None, description="캡처 시각 끝 범위", examples=["2026-08-31T23:59:59Z"])


class AssignAudioCaptureLabelsRequest(BaseRequest):
    label_option_ids: list[UUID] = Field(..., description="지정할 라벨 옵션 ID 목록", examples=[[]])


class UpdateAudioCaptureMemoRequest(BaseRequest):
    null_fields: ClassVar[set] = {"memo"}

    memo: str | None = Field(..., description="메모", examples=["소리가 선명함"])


class MigrateReviewLabelRequest(BaseRequest):
    category: str = Field(..., description="라벨 카테고리 이름", examples=["새 소리"])
    option: str = Field(..., description="라벨 옵션 이름", examples=["안녕"])


class MigrateReviewRequest(BaseRequest):
    empty_str_fields: ClassVar[set] = {"memo"}

    audio_file_id: str = Field(
        ...,
        description="S3 object key",
        examples=["audio_capture/{uid}/{capture_id}/{file_id}/session-xxx.wav"],
    )
    label: list[MigrateReviewLabelRequest] = Field(..., description="라벨 목록", examples=[[]])
    memo: str = Field(..., description="메모 내용", examples=[""])


class MigrateReviewsRequest(BaseRequest):
    reviews: list[MigrateReviewRequest] = Field(..., description="리뷰 목록", examples=[[]])


class ExportAudioSegmentsRequest(BaseRequest):
    null_fields: ClassVar[set] = {"audio_capture_label_option_ids"}

    audio_capture_label_option_ids: list[UUID] | None = Field(
        None,
        description="클립 라벨 옵션 ID 필터",
        examples=[[]],
    )


class GetWordSummaryDTO(CustomBaseModel):
    id: UUID = Field(..., description="ID")
    label: str = Field(..., description="단어명")


class GetWordDTO(GetWordSummaryDTO):
    allow_null_fields: ClassVar[set] = {
        "firebase_anon_uid",
        "device_platform",
        "device_os_version",
        "device_model",
    }

    firebase_anon_uid: str | None = Field(None, max_length=128, description="Firebase Authentication 익명 ID")
    client_word_id: str = Field(..., description="클라이언트 단어 ID")
    device_platform: str | None = Field(None, description="단어를 녹음한 기기의 OS")
    device_os_version: str | None = Field(None, description="단어를 녹음한 기기의 OS 버전")
    device_model: str | None = Field(None, description="단어를 녹음한 기기의 모델명")


class GetAudioCaptureDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"word", "duration_ms"}

    id: UUID = Field(..., description="캡처 ID")
    firebase_anon_uid: str = Field(..., max_length=128, description="Firebase Authentication 익명 ID")
    word: GetWordSummaryDTO | None = Field(None, description="연결된 단어 정보")
    cycle: int = Field(..., description="세션 사이클 번호")
    phase: PhaseEnum = Field(..., description="캡처 세션 구간")
    captured_at: datetime = Field(..., description="클라이언트 캡처 시각")
    duration_ms: int | None = Field(None, description="캡처 길이 ms")
    created_at: datetime = Field(..., description="서버 저장 시각")


class GetAudioCaptureListItemDTO(GetAudioCaptureDTO):
    allow_null_fields: ClassVar[set] = GetAudioCaptureDTO.allow_null_fields | {
        "parrot_species",
        "device_platform",
        "device_os_version",
        "device_model",
    }

    parrot_species: str | None = Field(None, description="앵무새 종")
    device_platform: str | None = Field(None, description="클립을 캡처한 기기의 OS")
    device_os_version: str | None = Field(None, description="클립을 캡처한 기기의 OS 버전")
    device_model: str | None = Field(None, description="클립을 캡처한 기기의 모델명")
    segment_count: int = Field(..., description="전체 세그먼트 수")
    labeled_count: int = Field(..., description="라벨링된 세그먼트 수")
    has_memo: bool = Field(..., description="메모가 있는 세그먼트 존재 여부")
    label_option_ids: list[UUID] = Field(..., description="클립 라벨 옵션 ID 목록")


class GetAudioCaptureDetailDTO(GetAudioCaptureDTO):
    allow_null_fields: ClassVar[set] = GetAudioCaptureDTO.allow_null_fields | {
        "parrot_species",
        "parrot_birthdate",
        "device_platform",
        "device_os_version",
        "device_model",
        "memo",
    }

    word: GetWordDTO | None = Field(None, description="연결된 단어 상세 정보")
    parrot_species: str | None = Field(None, description="앵무새 종")
    parrot_birthdate: date | None = Field(None, description="앵무새 생년월일")
    device_platform: str | None = Field(None, description="클립을 캡처한 기기의 OS")
    device_os_version: str | None = Field(None, description="클립을 캡처한 기기의 OS 버전")
    device_model: str | None = Field(None, description="클립을 캡처한 기기의 모델명")
    memo: str | None = Field(None, description="메모")
    audio_url: str = Field(..., description="원본 오디오 URL")
    segments: list[GetAudioSegmentDTO] = Field(..., description="세그먼트 목록")
    label_option_ids: list[UUID] = Field(..., description="클립 라벨 옵션 ID 목록")


class MigrateReviewResultDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"code", "error_code", "message"}

    status: Literal["success", "rejected"] = Field(..., description="항목의 마이그레이션 결과")
    code: int | None = Field(None, description="거부된 항목의 HTTP 상태 코드")
    error_code: str | None = Field(None, description="거부된 항목의 에러 코드")
    message: str | None = Field(None, description="거부된 항목의 에러 메시지")


class GetLabelListResponse(BaseResponse):
    data: list[GetLabelCategoryDTO]


class GetAudioCaptureListResponse(BaseResponse):
    data: list[GetAudioCaptureListItemDTO]


class GetAudioCaptureDetailResponse(BaseResponse):
    data: GetAudioCaptureDetailDTO


class MigrateReviewsResponse(BaseResponse):
    data: dict[str, MigrateReviewResultDTO]


class LoginDTO(CustomBaseModel):
    user_id: UUID
    is_new_user: bool


class LoginResponse(BaseResponse):
    data: LoginDTO


class ProfilePhotoDTO(CustomBaseModel):
    url: str


class UserDTO(CustomBaseModel):
    allow_null_fields: ClassVar[set] = {"email", "nickname", "photo"}

    id: UUID
    email: str | None
    nickname: str | None
    photo: ProfilePhotoDTO | None


class UserResponse(BaseResponse):
    data: UserDTO


class UpdateUserRequest(BaseRequest):
    null_fields: ClassVar[set] = {"nickname"}

    nickname: str | MISSING | None = MISSING

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, value: str | MISSING | None) -> str | MISSING | None:
        if not isinstance(value, str):
            return value

        value = unicodedata.normalize("NFC", value).strip(" ")
        if not value or not 2 <= len(value) <= 20 or re.fullmatch(r"[가-힣A-Za-z0-9_ ]+", value) is None:
            raise ValueError("닉네임은 한글, 영문, 숫자, 밑줄, 공백으로 구성된 2~20자여야 합니다.")
        return value

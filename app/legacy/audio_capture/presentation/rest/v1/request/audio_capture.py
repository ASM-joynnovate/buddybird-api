from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import Field

from core.common.request import BaseRequest, PageParams


class GetAudioCaptureListRequest(PageParams):
    null_fields: ClassVar[set] = {
        "firebase_anon_uid",
        "word_label",
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

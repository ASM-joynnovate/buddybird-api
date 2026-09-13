from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app import services
from app.dependencies import DBSession, Storage, verify_backoffice_password
from app.schemas import (
    AssignAudioCaptureLabelsRequest,
    AssignAudioSegmentLabelRequest,
    BaseResponse,
    CreateAudioSegmentRequest,
    ExportAudioSegmentsRequest,
    GetAudioCaptureDetailResponse,
    GetAudioCaptureListRequest,
    GetAudioCaptureListResponse,
    MigrateReviewsRequest,
    MigrateReviewsResponse,
    TrimAudioSegmentRequest,
    UpdateAudioCaptureMemoRequest,
    UpdateAudioSegmentMemoRequest,
)

router = APIRouter(dependencies=[Depends(verify_backoffice_password)])


@router.get("/captures", name="오디오 클립 목록 조회", response_model=GetAudioCaptureListResponse)
async def get_list(query: Annotated[GetAudioCaptureListRequest, Query()], db: DBSession) -> BaseResponse:
    items, total = await services.get_audio_capture_list(db=db, query=query)
    return BaseResponse(
        message="오디오 클립 목록 조회 성공",
        data=items,
        meta={
            "current_page": query.page,
            "total_page_count": (total + query.count_by_page - 1) // query.count_by_page,
            "is_first": query.page == 1,
            "is_last": query.page * query.count_by_page >= total,
        },
    )


@router.get(
    "/captures/{audio_capture_id:uuid}", name="오디오 클립 상세 조회", response_model=GetAudioCaptureDetailResponse
)
async def get_by_id(audio_capture_id: UUID, db: DBSession, storage: Storage) -> BaseResponse:
    return BaseResponse(
        message="오디오 클립 상세 조회 성공",
        data=await services.get_audio_capture_detail(audio_capture_id=audio_capture_id, db=db, storage=storage),
    )


@router.post("/captures/{audio_capture_id:uuid}/segments", name="오디오 세그먼트 추가")
async def create_audio_segment(
    audio_capture_id: UUID, body: CreateAudioSegmentRequest, db: DBSession, storage: Storage
) -> BaseResponse:
    return BaseResponse(
        message="오디오 세그먼트 추가 성공",
        data=await services.create_audio_segment(audio_capture_id=audio_capture_id, data=body, db=db, storage=storage),
    )


@router.put("/segments/{audio_segment_id:uuid}/trim", name="오디오 세그먼트 구간 수정")
async def trim_audio_segment(
    audio_segment_id: UUID, body: TrimAudioSegmentRequest, db: DBSession, storage: Storage
) -> BaseResponse:
    return BaseResponse(
        message="오디오 세그먼트 구간 수정 성공",
        data=await services.trim_audio_segment(audio_segment_id=audio_segment_id, data=body, db=db, storage=storage),
    )


@router.put("/segments/{audio_segment_id:uuid}/label", name="오디오 세그먼트 라벨 지정")
async def assign_audio_segment_label(
    audio_segment_id: UUID, body: AssignAudioSegmentLabelRequest, db: DBSession
) -> BaseResponse:
    return BaseResponse(
        message="오디오 세그먼트 라벨 지정 성공",
        data=await services.assign_audio_segment_label(audio_segment_id=audio_segment_id, data=body, db=db),
    )


@router.put("/segments/{audio_segment_id:uuid}/memo", name="오디오 세그먼트 메모 수정")
async def update_audio_segment_memo(
    audio_segment_id: UUID, body: UpdateAudioSegmentMemoRequest, db: DBSession
) -> BaseResponse:
    return BaseResponse(
        message="오디오 세그먼트 메모 수정 성공",
        data=await services.update_audio_segment_memo(audio_segment_id=audio_segment_id, data=body, db=db),
    )


@router.delete("/segments/{audio_segment_id:uuid}", name="오디오 세그먼트 삭제")
async def delete_audio_segment(audio_segment_id: UUID, db: DBSession) -> BaseResponse:
    return BaseResponse(
        message="오디오 세그먼트 삭제 성공",
        data=await services.delete_audio_segment(audio_segment_id=audio_segment_id, db=db),
    )


@router.put("/captures/{audio_capture_id:uuid}/labels", name="오디오 클립 라벨 지정")
async def assign_audio_capture_labels(
    audio_capture_id: UUID, body: AssignAudioCaptureLabelsRequest, db: DBSession
) -> BaseResponse:
    return BaseResponse(
        message="오디오 클립 라벨 지정 성공",
        data=await services.assign_audio_capture_labels(audio_capture_id=audio_capture_id, data=body, db=db),
    )


@router.put("/captures/{audio_capture_id:uuid}/memo", name="오디오 클립 메모 수정")
async def update_audio_capture_memo(
    audio_capture_id: UUID, body: UpdateAudioCaptureMemoRequest, db: DBSession
) -> BaseResponse:
    return BaseResponse(
        message="오디오 클립 메모 수정 성공",
        data=await services.update_audio_capture_memo(audio_capture_id=audio_capture_id, data=body, db=db),
    )


@router.put("/migrations/reviews", name="리뷰 마이그레이션", response_model=MigrateReviewsResponse)
async def migrate_reviews(body: MigrateReviewsRequest, db: DBSession) -> BaseResponse:
    return BaseResponse(message="리뷰 마이그레이션 성공", data=await services.migrate_reviews(data=body, db=db))


@router.get("/exports/segments", name="라벨링된 오디오 세그먼트 ZIP 내보내기")
async def export_audio_segments(
    query: Annotated[ExportAudioSegmentsRequest, Query()], db: DBSession, storage: Storage
) -> Response:
    return Response(
        content=await services.export_audio_segments(
            audio_capture_label_option_ids=query.audio_capture_label_option_ids, db=db, storage=storage
        ),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=audio_segments.zip"},
    )

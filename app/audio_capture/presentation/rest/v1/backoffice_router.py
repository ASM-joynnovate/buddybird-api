from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Response

from app.audio_capture.application.dto import (
    AssignAudioCaptureLabelsDTO,
    AssignAudioSegmentLabelDTO,
    CreateAudioSegmentDTO,
    CreateLabelCategoryDTO,
    CreateLabelOptionDTO,
    MigrateReviewsDTO,
    TrimAudioSegmentDTO,
    UpdateAudioCaptureMemoDTO,
    UpdateAudioSegmentMemoDTO,
    UpdateLabelCategoryDTO,
    UpdateLabelOptionDTO,
)
from app.audio_capture.application.use_cases.command.assign_audio_capture_labels import (
    AssignAudioCaptureLabelsUseCase,
)
from app.audio_capture.application.use_cases.command.assign_audio_segment_label import (
    AssignAudioSegmentLabelUseCase,
)
from app.audio_capture.application.use_cases.command.create_audio_segment import CreateAudioSegmentUseCase
from app.audio_capture.application.use_cases.command.create_label_category import CreateLabelCategoryUseCase
from app.audio_capture.application.use_cases.command.create_label_option import CreateLabelOptionUseCase
from app.audio_capture.application.use_cases.command.delete_audio_segment import DeleteAudioSegmentUseCase
from app.audio_capture.application.use_cases.command.delete_label_category import DeleteLabelCategoryUseCase
from app.audio_capture.application.use_cases.command.delete_label_option import DeleteLabelOptionUseCase
from app.audio_capture.application.use_cases.command.detect_audio_segments import DetectAudioSegmentsUseCase
from app.audio_capture.application.use_cases.command.migrate_reviews import MigrateReviewsUseCase
from app.audio_capture.application.use_cases.command.trim_audio_segment import TrimAudioSegmentUseCase
from app.audio_capture.application.use_cases.command.update_audio_capture_memo import UpdateAudioCaptureMemoUseCase
from app.audio_capture.application.use_cases.command.update_audio_segment_memo import UpdateAudioSegmentMemoUseCase
from app.audio_capture.application.use_cases.command.update_label_category import UpdateLabelCategoryUseCase
from app.audio_capture.application.use_cases.command.update_label_option import UpdateLabelOptionUseCase
from app.audio_capture.application.use_cases.query.export_audio_segment import ExportAudioSegmentsUseCase
from app.audio_capture.application.use_cases.query.get_audio_capture_count import GetAudioCaptureCountUseCase
from app.audio_capture.application.use_cases.query.get_audio_capture_detail import GetAudioCaptureDetailUseCase
from app.audio_capture.application.use_cases.query.get_audio_capture_list import GetAudioCaptureListUseCase
from app.audio_capture.application.use_cases.query.get_label_list import GetLabelListUseCase
from app.audio_capture.presentation.rest.v1.dependencies import verify_backoffice_password
from app.audio_capture.presentation.rest.v1.request import (
    AssignAudioCaptureLabelsRequest,
    AssignAudioSegmentLabelRequest,
    CreateAudioSegmentRequest,
    CreateLabelCategoryRequest,
    CreateLabelOptionRequest,
    ExportAudioSegmentsRequest,
    GetAudioCaptureListRequest,
    MigrateReviewsRequest,
    TrimAudioSegmentRequest,
    UpdateAudioCaptureMemoRequest,
    UpdateAudioSegmentMemoRequest,
    UpdateLabelCategoryRequest,
    UpdateLabelOptionRequest,
)
from app.audio_capture.presentation.rest.v1.response import (
    GetAudioCaptureDetailResponse,
    GetAudioCaptureListResponse,
    GetLabelListResponse,
    MigrateReviewsResponse,
)
from app.container import AppContainer
from core.common.response import BaseResponse
from core.helpers.meta import generate_page_metadata

router = APIRouter(dependencies=[Depends(verify_backoffice_password)])


@router.get("/labels", name="라벨 목록 조회", response_model=GetLabelListResponse)
@inject
async def get_labels(
    use_case: Annotated[
        GetLabelListUseCase,
        Depends(Provide[AppContainer.audio_capture.get_label_list_query]),
    ],
) -> BaseResponse:
    return BaseResponse(message="라벨 목록 조회 성공", data=await use_case.execute())


@router.post("/labels/categories", name="라벨 카테고리 생성", response_model=BaseResponse)
@inject
async def create_label_category(
    body: CreateLabelCategoryRequest,
    use_case: Annotated[
        CreateLabelCategoryUseCase, Depends(Provide[AppContainer.audio_capture.create_label_category_command])
    ],
) -> BaseResponse:
    data = CreateLabelCategoryDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(message="라벨 카테고리 생성 성공", data=await use_case.execute(data=data))


@router.patch("/labels/categories/{label_category_id:uuid}", name="라벨 카테고리 수정", response_model=BaseResponse)
@inject
async def update_label_category(
    label_category_id: UUID,
    body: UpdateLabelCategoryRequest,
    use_case: Annotated[
        UpdateLabelCategoryUseCase, Depends(Provide[AppContainer.audio_capture.update_label_category_command])
    ],
) -> BaseResponse:
    data = UpdateLabelCategoryDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(
        message="라벨 카테고리 수정 성공",
        data=await use_case.execute(label_category_id=label_category_id, data=data),
    )


@router.delete("/labels/categories/{label_category_id:uuid}", name="라벨 카테고리 삭제", response_model=BaseResponse)
@inject
async def delete_label_category(
    label_category_id: UUID,
    use_case: Annotated[
        DeleteLabelCategoryUseCase, Depends(Provide[AppContainer.audio_capture.delete_label_category_command])
    ],
) -> BaseResponse:
    return BaseResponse(
        message="라벨 카테고리 삭제 성공",
        data=await use_case.execute(label_category_id=label_category_id),
    )


@router.post(
    "/labels/categories/{label_category_id:uuid}/options",
    name="라벨 옵션 생성",
    response_model=BaseResponse,
)
@inject
async def create_label_option(
    label_category_id: UUID,
    body: CreateLabelOptionRequest,
    use_case: Annotated[
        CreateLabelOptionUseCase, Depends(Provide[AppContainer.audio_capture.create_label_option_command])
    ],
) -> BaseResponse:
    data = CreateLabelOptionDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(
        message="라벨 옵션 생성 성공",
        data=await use_case.execute(label_category_id=label_category_id, data=data),
    )


@router.patch("/labels/options/{label_option_id:uuid}", name="라벨 옵션 수정", response_model=BaseResponse)
@inject
async def update_label_option(
    label_option_id: UUID,
    body: UpdateLabelOptionRequest,
    use_case: Annotated[
        UpdateLabelOptionUseCase, Depends(Provide[AppContainer.audio_capture.update_label_option_command])
    ],
) -> BaseResponse:
    data = UpdateLabelOptionDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(
        message="라벨 옵션 수정 성공",
        data=await use_case.execute(label_option_id=label_option_id, data=data),
    )


@router.delete("/labels/options/{label_option_id:uuid}", name="라벨 옵션 삭제", response_model=BaseResponse)
@inject
async def delete_label_option(
    label_option_id: UUID,
    use_case: Annotated[
        DeleteLabelOptionUseCase, Depends(Provide[AppContainer.audio_capture.delete_label_option_command])
    ],
) -> BaseResponse:
    return BaseResponse(
        message="라벨 옵션 삭제 성공",
        data=await use_case.execute(label_option_id=label_option_id),
    )


@router.get("/captures", name="오디오 클립 목록 조회", response_model=GetAudioCaptureListResponse)
@inject
async def get_list(
    query: Annotated[GetAudioCaptureListRequest, Query()],
    list_use_case: Annotated[
        GetAudioCaptureListUseCase,
        Depends(Provide[AppContainer.audio_capture.get_audio_capture_list_query]),
    ],
    count_use_case: Annotated[
        GetAudioCaptureCountUseCase,
        Depends(Provide[AppContainer.audio_capture.get_audio_capture_count_query]),
    ],
) -> BaseResponse:
    prev, limit = query.to_prev_limit()

    items = await list_use_case.execute(
        firebase_anon_uid=query.firebase_anon_uid,
        word_label=query.word_label,
        label_option_ids=query.label_option_ids,
        has_memo=query.has_memo,
        date_from=query.date_from,
        date_to=query.date_to,
        prev=prev,
        limit=limit,
    )
    total = await count_use_case.execute(
        firebase_anon_uid=query.firebase_anon_uid,
        word_label=query.word_label,
        label_option_ids=query.label_option_ids,
        has_memo=query.has_memo,
        date_from=query.date_from,
        date_to=query.date_to,
    )

    return BaseResponse(
        message="오디오 클립 목록 조회 성공",
        data=items,
        meta=generate_page_metadata(count=total, page=query.page, limit=query.count_by_page),
    )


@router.get(
    "/captures/{audio_capture_id:uuid}", name="오디오 클립 상세 조회", response_model=GetAudioCaptureDetailResponse
)
@inject
async def get_by_id(
    audio_capture_id: UUID,
    use_case: Annotated[
        GetAudioCaptureDetailUseCase,
        Depends(Provide[AppContainer.audio_capture.get_audio_capture_detail_query]),
    ],
) -> BaseResponse:
    return BaseResponse(
        message="오디오 클립 상세 조회 성공",
        data=await use_case.execute(audio_capture_id=audio_capture_id),
    )


@router.post("/captures/{audio_capture_id:uuid}/segments", name="오디오 세그먼트 추가", response_model=BaseResponse)
@inject
async def create_audio_segment(
    audio_capture_id: UUID,
    body: CreateAudioSegmentRequest,
    use_case: Annotated[
        CreateAudioSegmentUseCase, Depends(Provide[AppContainer.audio_capture.create_audio_segment_command])
    ],
) -> BaseResponse:
    data = CreateAudioSegmentDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(
        message="오디오 세그먼트 추가 성공",
        data=await use_case.execute(audio_capture_id=audio_capture_id, data=data),
    )


@router.post("/captures/{audio_capture_id:uuid}/vad", name="VAD 오디오 세그먼트 자동 생성", response_model=BaseResponse)
@inject
async def detect_audio_segments(
    audio_capture_id: UUID,
    use_case: Annotated[
        DetectAudioSegmentsUseCase, Depends(Provide[AppContainer.audio_capture.detect_audio_segments_command])
    ],
) -> BaseResponse:
    return BaseResponse(
        message="VAD 오디오 세그먼트 자동 생성 성공",
        data=await use_case.execute(audio_capture_id=audio_capture_id),
    )


@router.put("/segments/{audio_segment_id:uuid}/trim", name="오디오 세그먼트 구간 수정", response_model=BaseResponse)
@inject
async def trim_audio_segment(
    audio_segment_id: UUID,
    body: TrimAudioSegmentRequest,
    use_case: Annotated[
        TrimAudioSegmentUseCase, Depends(Provide[AppContainer.audio_capture.trim_audio_segment_command])
    ],
) -> BaseResponse:
    data = TrimAudioSegmentDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(
        message="오디오 세그먼트 구간 수정 성공",
        data=await use_case.execute(audio_segment_id=audio_segment_id, data=data),
    )


@router.put("/segments/{audio_segment_id:uuid}/label", name="오디오 세그먼트 라벨 지정", response_model=BaseResponse)
@inject
async def assign_audio_segment_label(
    audio_segment_id: UUID,
    body: AssignAudioSegmentLabelRequest,
    use_case: Annotated[
        AssignAudioSegmentLabelUseCase,
        Depends(Provide[AppContainer.audio_capture.assign_audio_segment_label_command]),
    ],
) -> BaseResponse:
    data = AssignAudioSegmentLabelDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(
        message="오디오 세그먼트 라벨 지정 성공",
        data=await use_case.execute(audio_segment_id=audio_segment_id, data=data),
    )


@router.put("/segments/{audio_segment_id:uuid}/memo", name="오디오 세그먼트 메모 수정", response_model=BaseResponse)
@inject
async def update_audio_segment_memo(
    audio_segment_id: UUID,
    body: UpdateAudioSegmentMemoRequest,
    use_case: Annotated[
        UpdateAudioSegmentMemoUseCase,
        Depends(Provide[AppContainer.audio_capture.update_audio_segment_memo_command]),
    ],
) -> BaseResponse:
    data = UpdateAudioSegmentMemoDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(
        message="오디오 세그먼트 메모 수정 성공",
        data=await use_case.execute(audio_segment_id=audio_segment_id, data=data),
    )


@router.delete("/segments/{audio_segment_id:uuid}", name="오디오 세그먼트 삭제", response_model=BaseResponse)
@inject
async def delete_audio_segment(
    audio_segment_id: UUID,
    use_case: Annotated[
        DeleteAudioSegmentUseCase, Depends(Provide[AppContainer.audio_capture.delete_audio_segment_command])
    ],
) -> BaseResponse:
    return BaseResponse(
        message="오디오 세그먼트 삭제 성공",
        data=await use_case.execute(audio_segment_id=audio_segment_id),
    )


@router.put("/captures/{audio_capture_id:uuid}/labels", name="오디오 클립 라벨 지정", response_model=BaseResponse)
@inject
async def assign_audio_capture_labels(
    audio_capture_id: UUID,
    body: AssignAudioCaptureLabelsRequest,
    use_case: Annotated[
        AssignAudioCaptureLabelsUseCase,
        Depends(Provide[AppContainer.audio_capture.assign_audio_capture_labels_command]),
    ],
) -> BaseResponse:
    data = AssignAudioCaptureLabelsDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(
        message="오디오 클립 라벨 지정 성공",
        data=await use_case.execute(audio_capture_id=audio_capture_id, data=data),
    )


@router.put("/captures/{audio_capture_id:uuid}/memo", name="오디오 클립 메모 수정", response_model=BaseResponse)
@inject
async def update_audio_capture_memo(
    audio_capture_id: UUID,
    body: UpdateAudioCaptureMemoRequest,
    use_case: Annotated[
        UpdateAudioCaptureMemoUseCase,
        Depends(Provide[AppContainer.audio_capture.update_audio_capture_memo_command]),
    ],
) -> BaseResponse:
    data = UpdateAudioCaptureMemoDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(
        message="오디오 클립 메모 수정 성공",
        data=await use_case.execute(audio_capture_id=audio_capture_id, data=data),
    )


@router.put("/migrations/reviews", name="리뷰 마이그레이션", response_model=MigrateReviewsResponse)
@inject
async def migrate_reviews(
    body: MigrateReviewsRequest,
    use_case: Annotated[
        MigrateReviewsUseCase,
        Depends(Provide[AppContainer.audio_capture.migrate_reviews_command]),
    ],
) -> BaseResponse:
    data = MigrateReviewsDTO(**body.model_dump(exclude_unset=True))

    return BaseResponse(message="리뷰 마이그레이션 성공", data=await use_case.execute(data=data))


@router.get("/exports/segments", name="라벨링된 오디오 세그먼트 ZIP 내보내기")
@inject
async def export_audio_segments(
    query: Annotated[ExportAudioSegmentsRequest, Query()],
    use_case: Annotated[
        ExportAudioSegmentsUseCase, Depends(Provide[AppContainer.audio_capture.export_audio_segments_query])
    ],
) -> Response:
    return Response(
        content=await use_case.execute(
            audio_capture_label_option_ids=query.audio_capture_label_option_ids,
        ),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=audio_segments.zip"},
    )

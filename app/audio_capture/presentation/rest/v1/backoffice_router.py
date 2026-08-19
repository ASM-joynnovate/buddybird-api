from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Response

from app.audio_capture.application.dto.audio_segment import (
    AssignAudioSegmentLabelDTO,
    CreateAudioSegmentDTO,
    TrimAudioSegmentDTO,
)
from app.audio_capture.application.dto.label import (
    CreateLabelCategoryDTO,
    CreateLabelOptionDTO,
    UpdateLabelCategoryDTO,
    UpdateLabelOptionDTO,
)
from app.audio_capture.application.use_cases.command.manage_labels import (
    CreateLabelCategoryUseCase,
    CreateLabelOptionUseCase,
    DeleteLabelCategoryUseCase,
    DeleteLabelOptionUseCase,
    UpdateLabelCategoryUseCase,
    UpdateLabelOptionUseCase,
)
from app.audio_capture.application.use_cases.command.manage_segments import (
    AssignAudioSegmentLabelUseCase,
    CreateAudioSegmentUseCase,
    DeleteAudioSegmentUseCase,
    DetectAudioSegmentsUseCase,
    TrimAudioSegmentUseCase,
)
from app.audio_capture.application.use_cases.query.audio_capture import AudioCaptureQueryUseCase
from app.audio_capture.application.use_cases.query.export_audio_segment import ExportAudioSegmentsUseCase
from app.audio_capture.application.use_cases.query.label import LabelQueryUseCase
from app.audio_capture.presentation.rest.v1.dependencies import verify_backoffice_password
from app.audio_capture.presentation.rest.v1.response.audio_capture import (
    GetAudioCaptureDetailResponse,
    GetAudioCaptureListResponse,
)
from app.audio_capture.presentation.rest.v1.response.label import GetLabelListResponse
from app.container import AppContainer
from core.common.response import BaseResponse
from core.helpers.meta import MetaDataHelper

from .request import (
    AssignAudioSegmentLabelRequest,
    CreateAudioSegmentRequest,
    CreateLabelCategoryRequest,
    CreateLabelOptionRequest,
    GetAudioCaptureListRequest,
    TrimAudioSegmentRequest,
    UpdateLabelCategoryRequest,
    UpdateLabelOptionRequest,
)

router = APIRouter(dependencies=[Depends(verify_backoffice_password)])


@router.get("/labels", name="라벨 목록 조회", response_model=GetLabelListResponse)
@inject
async def get_labels(
    use_case: Annotated[LabelQueryUseCase, Depends(Provide[AppContainer.audio_capture.label_query])],
):
    return BaseResponse(message="라벨 목록 조회 성공", data=await use_case.get_list())


@router.post("/labels/categories", name="라벨 카테고리 생성", response_model=BaseResponse)
@inject
async def create_label_category(
    body: CreateLabelCategoryRequest,
    use_case: Annotated[
        CreateLabelCategoryUseCase, Depends(Provide[AppContainer.audio_capture.create_label_category_command])
    ],
):
    data = CreateLabelCategoryDTO(**body.model_dump(exclude_unset=True))
    await use_case.execute(data=data)
    return BaseResponse(message="라벨 카테고리 생성 성공")


@router.put("/labels/categories/{label_category_id:uuid}", name="라벨 카테고리 수정", response_model=BaseResponse)
@inject
async def update_label_category(
    label_category_id: UUID,
    body: UpdateLabelCategoryRequest,
    use_case: Annotated[
        UpdateLabelCategoryUseCase, Depends(Provide[AppContainer.audio_capture.update_label_category_command])
    ],
):
    data = UpdateLabelCategoryDTO(**body.model_dump(exclude_unset=True))
    await use_case.execute(label_category_id=label_category_id, data=data)
    return BaseResponse(message="라벨 카테고리 수정 성공")


@router.delete("/labels/categories/{label_category_id:uuid}", name="라벨 카테고리 삭제", response_model=BaseResponse)
@inject
async def delete_label_category(
    label_category_id: UUID,
    use_case: Annotated[
        DeleteLabelCategoryUseCase, Depends(Provide[AppContainer.audio_capture.delete_label_category_command])
    ],
):
    await use_case.execute(label_category_id=label_category_id)
    return BaseResponse(message="라벨 카테고리 삭제 성공")


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
):
    data = CreateLabelOptionDTO(**body.model_dump(exclude_unset=True))
    await use_case.execute(label_category_id=label_category_id, data=data)

    return BaseResponse(message="라벨 옵션 생성 성공")


@router.put("/labels/options/{label_option_id:uuid}", name="라벨 옵션 수정", response_model=BaseResponse)
@inject
async def update_label_option(
    label_option_id: UUID,
    body: UpdateLabelOptionRequest,
    use_case: Annotated[
        UpdateLabelOptionUseCase, Depends(Provide[AppContainer.audio_capture.update_label_option_command])
    ],
):
    data = UpdateLabelOptionDTO(**body.model_dump(exclude_unset=True))
    await use_case.execute(label_option_id=label_option_id, data=data)

    return BaseResponse(message="라벨 옵션 수정 성공")


@router.delete("/labels/options/{label_option_id:uuid}", name="라벨 옵션 삭제", response_model=BaseResponse)
@inject
async def delete_label_option(
    label_option_id: UUID,
    use_case: Annotated[
        DeleteLabelOptionUseCase, Depends(Provide[AppContainer.audio_capture.delete_label_option_command])
    ],
):
    await use_case.execute(label_option_id=label_option_id)

    return BaseResponse(message="라벨 옵션 삭제 성공")


@router.get("/captures", name="오디오 클립 목록 조회", response_model=GetAudioCaptureListResponse)
@inject
async def get_captures(
    query: Annotated[GetAudioCaptureListRequest, Query()],
    use_case: Annotated[AudioCaptureQueryUseCase, Depends(Provide[AppContainer.audio_capture.audio_capture_query])],
):
    prev, limit = query.to_prev_limit()

    items = await use_case.get_list(
        firebase_anon_uid=query.firebase_anon_uid,
        word_label=query.word_label,
        label_status=query.label_status,
        date_from=query.date_from,
        date_to=query.date_to,
        prev=prev,
        limit=limit,
    )
    total = await use_case.get_count(
        firebase_anon_uid=query.firebase_anon_uid,
        word_label=query.word_label,
        label_status=query.label_status,
        date_from=query.date_from,
        date_to=query.date_to,
    )

    return BaseResponse(
        message="오디오 클립 목록 조회 성공",
        data=items,
        meta=MetaDataHelper.generate_page_metadata(count=total, page=query.page, limit=query.count_by_page),
    )


@router.get(
    "/captures/{audio_capture_id:uuid}", name="오디오 클립 상세 조회", response_model=GetAudioCaptureDetailResponse
)
@inject
async def get_capture(
    audio_capture_id: UUID,
    use_case: Annotated[AudioCaptureQueryUseCase, Depends(Provide[AppContainer.audio_capture.audio_capture_query])],
):
    return BaseResponse(
        message="오디오 클립 상세 조회 성공",
        data=await use_case.get_detail(audio_capture_id=audio_capture_id),
    )


@router.post("/captures/{audio_capture_id:uuid}/segments", name="오디오 세그먼트 추가", response_model=BaseResponse)
@inject
async def create_audio_segment(
    audio_capture_id: UUID,
    body: CreateAudioSegmentRequest,
    use_case: Annotated[
        CreateAudioSegmentUseCase, Depends(Provide[AppContainer.audio_capture.create_audio_segment_command])
    ],
):
    data = CreateAudioSegmentDTO(**body.model_dump(exclude_unset=True))
    await use_case.execute(audio_capture_id=audio_capture_id, data=data)

    return BaseResponse(message="오디오 세그먼트 추가 성공")


@router.post("/captures/{audio_capture_id:uuid}/vad", name="VAD 오디오 세그먼트 자동 생성", response_model=BaseResponse)
@inject
async def detect_audio_segments(
    audio_capture_id: UUID,
    use_case: Annotated[
        DetectAudioSegmentsUseCase, Depends(Provide[AppContainer.audio_capture.detect_audio_segments_command])
    ],
):
    await use_case.execute(audio_capture_id=audio_capture_id)

    return BaseResponse(message="VAD 오디오 세그먼트 자동 생성 성공")


@router.put("/segments/{audio_segment_id:uuid}/trim", name="오디오 세그먼트 구간 수정", response_model=BaseResponse)
@inject
async def trim_audio_segment(
    audio_segment_id: UUID,
    body: TrimAudioSegmentRequest,
    use_case: Annotated[
        TrimAudioSegmentUseCase, Depends(Provide[AppContainer.audio_capture.trim_audio_segment_command])
    ],
):
    data = TrimAudioSegmentDTO(**body.model_dump(exclude_unset=True))
    await use_case.execute(audio_segment_id=audio_segment_id, data=data)

    return BaseResponse(message="오디오 세그먼트 구간 수정 성공")


@router.put("/segments/{audio_segment_id:uuid}/label", name="오디오 세그먼트 라벨 지정", response_model=BaseResponse)
@inject
async def assign_audio_segment_label(
    audio_segment_id: UUID,
    body: AssignAudioSegmentLabelRequest,
    use_case: Annotated[
        AssignAudioSegmentLabelUseCase,
        Depends(Provide[AppContainer.audio_capture.assign_audio_segment_label_command]),
    ],
):
    data = AssignAudioSegmentLabelDTO(**body.model_dump(exclude_unset=True))
    await use_case.execute(audio_segment_id=audio_segment_id, data=data)

    return BaseResponse(message="오디오 세그먼트 라벨 지정 성공")


@router.delete("/segments/{audio_segment_id:uuid}", name="오디오 세그먼트 삭제", response_model=BaseResponse)
@inject
async def delete_audio_segment(
    audio_segment_id: UUID,
    use_case: Annotated[
        DeleteAudioSegmentUseCase, Depends(Provide[AppContainer.audio_capture.delete_audio_segment_command])
    ],
):
    await use_case.execute(audio_segment_id=audio_segment_id)

    return BaseResponse(message="오디오 세그먼트 삭제 성공")


@router.get("/exports/segments", name="라벨링된 오디오 세그먼트 ZIP 내보내기")
@inject
async def export_audio_segments(
    use_case: Annotated[
        ExportAudioSegmentsUseCase, Depends(Provide[AppContainer.audio_capture.export_audio_segments_query])
    ],
):
    return Response(
        content=await use_case.execute(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=audio_segments.zip"},
    )

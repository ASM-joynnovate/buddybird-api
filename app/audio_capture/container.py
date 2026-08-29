from dependency_injector import containers, providers

from app.audio_capture.application.use_cases.command.assign_audio_capture_labels import AssignAudioCaptureLabelsUseCase
from app.audio_capture.application.use_cases.command.batch_create_audio_capture import BatchCreateAudioCaptureUseCase
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
    UpdateAudioSegmentMemoUseCase,
)
from app.audio_capture.application.use_cases.query.audio_capture import AudioCaptureQueryUseCase
from app.audio_capture.application.use_cases.query.export_audio_segment import ExportAudioSegmentsUseCase
from app.audio_capture.application.use_cases.query.label import LabelQueryUseCase
from app.audio_capture.infra.presistance import (
    SQLAlchemyAudioCaptureRepo,
    SQLAlchemyAudioSegmentRepo,
    SQLAlchemyLabelCategoryRepo,
    SQLAlchemyLabelOptionRepo,
)
from app.audio_capture.infra.services import SileroVadService, WaveAudioAnalyzer


class AudioCaptureContainer(containers.DeclarativeContainer):
    object_storage_client = providers.Dependency()
    file_analyzer = providers.Dependency()

    audio_analyzer = providers.Singleton(WaveAudioAnalyzer)
    vad_service = providers.Singleton(SileroVadService)
    audio_capture_repo = providers.Singleton(SQLAlchemyAudioCaptureRepo)

    batch_create_audio_capture_command = providers.Factory(
        BatchCreateAudioCaptureUseCase,
        audio_capture_repo=audio_capture_repo,
        object_storage_client=object_storage_client,
        file_analyzer=file_analyzer,
        audio_analyzer=audio_analyzer,
    )

    audio_segment_repo = providers.Singleton(SQLAlchemyAudioSegmentRepo)

    audio_capture_query = providers.Factory(
        AudioCaptureQueryUseCase,
        audio_capture_repo=audio_capture_repo,
        audio_segment_repo=audio_segment_repo,
        object_storage_client=object_storage_client,
    )

    label_category_repo = providers.Singleton(SQLAlchemyLabelCategoryRepo)
    label_option_repo = providers.Singleton(SQLAlchemyLabelOptionRepo)

    label_query = providers.Factory(
        LabelQueryUseCase,
        label_category_repo=label_category_repo,
    )
    create_label_category_command = providers.Factory(
        CreateLabelCategoryUseCase,
        label_category_repo=label_category_repo,
    )
    update_label_category_command = providers.Factory(
        UpdateLabelCategoryUseCase,
        label_category_repo=label_category_repo,
    )
    delete_label_category_command = providers.Factory(
        DeleteLabelCategoryUseCase,
        label_category_repo=label_category_repo,
        audio_segment_repo=audio_segment_repo,
        audio_capture_repo=audio_capture_repo,
    )
    create_label_option_command = providers.Factory(
        CreateLabelOptionUseCase,
        label_category_repo=label_category_repo,
        label_option_repo=label_option_repo,
    )
    update_label_option_command = providers.Factory(
        UpdateLabelOptionUseCase,
        label_option_repo=label_option_repo,
    )
    delete_label_option_command = providers.Factory(
        DeleteLabelOptionUseCase,
        label_option_repo=label_option_repo,
        audio_segment_repo=audio_segment_repo,
        audio_capture_repo=audio_capture_repo,
    )

    create_audio_segment_command = providers.Factory(
        CreateAudioSegmentUseCase,
        object_storage_client=object_storage_client,
        audio_analyzer=audio_analyzer,
        audio_capture_repo=audio_capture_repo,
        audio_segment_repo=audio_segment_repo,
    )
    trim_audio_segment_command = providers.Factory(
        TrimAudioSegmentUseCase,
        object_storage_client=object_storage_client,
        audio_analyzer=audio_analyzer,
        audio_capture_repo=audio_capture_repo,
        audio_segment_repo=audio_segment_repo,
    )
    delete_audio_segment_command = providers.Factory(
        DeleteAudioSegmentUseCase,
        audio_segment_repo=audio_segment_repo,
    )
    assign_audio_capture_labels_command = providers.Factory(
        AssignAudioCaptureLabelsUseCase,
        audio_capture_repo=audio_capture_repo,
        label_option_repo=label_option_repo,
        label_category_repo=label_category_repo,
    )
    assign_audio_segment_label_command = providers.Factory(
        AssignAudioSegmentLabelUseCase,
        audio_segment_repo=audio_segment_repo,
        label_option_repo=label_option_repo,
        label_category_repo=label_category_repo,
    )
    update_audio_segment_memo_command = providers.Factory(
        UpdateAudioSegmentMemoUseCase,
        audio_segment_repo=audio_segment_repo,
    )
    detect_audio_segments_command = providers.Factory(
        DetectAudioSegmentsUseCase,
        object_storage_client=object_storage_client,
        audio_analyzer=audio_analyzer,
        vad_service=vad_service,
        audio_capture_repo=audio_capture_repo,
        audio_segment_repo=audio_segment_repo,
    )

    export_audio_segments_query = providers.Factory(
        ExportAudioSegmentsUseCase,
        audio_segment_repo=audio_segment_repo,
        label_category_repo=label_category_repo,
        object_storage_client=object_storage_client,
    )

from dependency_injector import containers, providers
from silero_vad import load_silero_vad

from app.audio_capture.application.use_cases.command.assign_audio_capture_labels import AssignAudioCaptureLabelsUseCase
from app.audio_capture.application.use_cases.command.assign_audio_segment_label import AssignAudioSegmentLabelUseCase
from app.audio_capture.application.use_cases.command.batch_create_audio_capture import BatchCreateAudioCaptureUseCase
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
from app.audio_capture.infra.persistence import (
    AudioCaptureSQLAlchemyRepo,
    AudioSegmentSQLAlchemyRepo,
    LabelCategorySQLAlchemyRepo,
    LabelOptionSQLAlchemyRepo,
)
from app.audio_capture.infra.services import SileroVadService, WaveAudioAnalyzer


class AudioCaptureContainer(containers.DeclarativeContainer):
    object_storage_client = providers.Dependency()
    file_analyzer = providers.Dependency()

    audio_analyzer = providers.Singleton(WaveAudioAnalyzer)
    vad_model = providers.Singleton(load_silero_vad)
    vad_service = providers.Singleton(SileroVadService, model=vad_model)
    audio_capture_repo = providers.Singleton(AudioCaptureSQLAlchemyRepo)

    batch_create_audio_capture_command = providers.Factory(
        BatchCreateAudioCaptureUseCase,
        object_storage_client=object_storage_client,
        file_analyzer=file_analyzer,
        audio_analyzer=audio_analyzer,
        audio_capture_repo=audio_capture_repo,
    )

    audio_segment_repo = providers.Singleton(AudioSegmentSQLAlchemyRepo)

    get_audio_capture_list_query = providers.Factory(
        GetAudioCaptureListUseCase,
        audio_capture_repo=audio_capture_repo,
        audio_segment_repo=audio_segment_repo,
    )
    get_audio_capture_count_query = providers.Factory(
        GetAudioCaptureCountUseCase,
        audio_capture_repo=audio_capture_repo,
    )
    get_audio_capture_detail_query = providers.Factory(
        GetAudioCaptureDetailUseCase,
        audio_capture_repo=audio_capture_repo,
        audio_segment_repo=audio_segment_repo,
        object_storage_client=object_storage_client,
    )

    label_category_repo = providers.Singleton(LabelCategorySQLAlchemyRepo)
    label_option_repo = providers.Singleton(LabelOptionSQLAlchemyRepo)

    get_label_list_query = providers.Factory(
        GetLabelListUseCase,
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
    migrate_reviews_command = providers.Factory(
        MigrateReviewsUseCase,
        audio_capture_repo=audio_capture_repo,
        label_category_repo=label_category_repo,
    )
    assign_audio_capture_labels_command = providers.Factory(
        AssignAudioCaptureLabelsUseCase,
        audio_capture_repo=audio_capture_repo,
        label_option_repo=label_option_repo,
        label_category_repo=label_category_repo,
    )
    update_audio_capture_memo_command = providers.Factory(
        UpdateAudioCaptureMemoUseCase,
        audio_capture_repo=audio_capture_repo,
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

from dependency_injector import containers, providers

from app.audio_capture.application.use_cases.command.batch_create_audio_capture import BatchCreateAudioCaptureUseCase
from app.audio_capture.infra.presistance import SQLAlchemyAudioCaptureRepo
from app.audio_capture.infra.services import WaveAudioAnalyzer


class AudioCaptureContainer(containers.DeclarativeContainer):
    object_storage_client = providers.Dependency()
    file_analyzer = providers.Dependency()

    audio_analyzer = providers.Singleton(WaveAudioAnalyzer)
    audio_capture_repo = providers.Singleton(SQLAlchemyAudioCaptureRepo)

    batch_create_audio_capture_command = providers.Factory(
        BatchCreateAudioCaptureUseCase,
        audio_capture_repo=audio_capture_repo,
        object_storage_client=object_storage_client,
        file_analyzer=file_analyzer,
        audio_analyzer=audio_analyzer,
    )

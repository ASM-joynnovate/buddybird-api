from dependency_injector import containers, providers
from dependency_injector.containers import DeclarativeContainer

from app.audio_capture.container import AudioCaptureContainer
from app.shared_kernel.infra.object_storages import S3StorageClient
from app.shared_kernel.infra.services import MagicFileAnalyzer
from app.word.container import WordContainer


class AppContainer(DeclarativeContainer):
    config = providers.Configuration()
    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.word.presentation",
            "app.audio_capture.presentation",
        ]
    )

    object_storage_client = providers.Singleton(S3StorageClient)
    file_analyzer = providers.Singleton(MagicFileAnalyzer)

    word = providers.Container(
        WordContainer,
        object_storage_client=object_storage_client,
        file_analyzer=file_analyzer,
    )

    audio_capture = providers.Container(
        AudioCaptureContainer,
        object_storage_client=object_storage_client,
        file_analyzer=file_analyzer,
    )

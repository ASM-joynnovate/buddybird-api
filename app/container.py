import boto3
from dependency_injector import containers, providers

from app.audio_capture.container import AudioCaptureContainer
from app.shared_kernel.infra.object_storages import S3StorageClient
from app.shared_kernel.infra.services import MagicFileAnalyzer
from app.word.container import WordContainer
from core.config import config as app_settings
from core.helpers.cache import CacheManager, CustomKeyMaker, RedisBackend
from core.helpers.redis import RedisHelper


class AppContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.word.presentation",
            "app.audio_capture.presentation",
        ]
    )

    s3_client = providers.Singleton(
        boto3.client,
        service_name="s3",
        endpoint_url=app_settings.S3_ENDPOINT_URL,
        aws_access_key_id=app_settings.S3_ACCESS_KEY,
        aws_secret_access_key=app_settings.S3_SECRET_KEY,
        region_name=app_settings.S3_REGION,
    )
    object_storage_client = providers.Singleton(S3StorageClient, client=s3_client)
    file_analyzer = providers.Singleton(MagicFileAnalyzer)
    redis_helper = providers.Singleton(RedisHelper)
    cache_backend = providers.Singleton(RedisBackend, redis_helper=redis_helper)
    cache_key_maker = providers.Singleton(CustomKeyMaker)
    cache = providers.Singleton(CacheManager, backend=cache_backend, key_maker=cache_key_maker)

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

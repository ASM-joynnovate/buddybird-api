from app.enums import FileStatusEnum
from app.models import File
from app.s3 import S3StorageClient
from app.schemas.base import FileDTO, PublicFileDTO


def build_file_dto(*, storage: S3StorageClient, file: File | None) -> FileDTO | None:
    if file is None:
        return None

    return FileDTO(url=storage.generate_presigned_url(path=file.object_key), status=FileStatusEnum(file.status))


def build_public_file_dto(*, storage: S3StorageClient, file: File | None) -> PublicFileDTO | None:
    if file is None:
        return None

    return PublicFileDTO(url=storage.generate_presigned_url(path=file.object_key))

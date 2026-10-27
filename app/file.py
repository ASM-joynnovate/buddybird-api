import asyncio
import io

from PIL import Image, ImageOps, UnidentifiedImageError

from app.enums import FileStatusEnum
from app.errors import InvalidProfilePhotoError, ResourceNotFoundError
from app.models import File
from app.s3 import S3StorageClient
from app.schemas.base import FileDTO, PublicFileDTO

MAX_PHOTO_PIXELS = 20_000_000


def build_file_dto(*, storage: S3StorageClient, file: File | None) -> FileDTO | None:
    if file is None:
        return None

    return FileDTO(url=storage.generate_presigned_url(path=file.object_key), status=FileStatusEnum(file.status))


def build_public_file_dto(*, storage: S3StorageClient, file: File | None) -> PublicFileDTO | None:
    if file is None:
        return None

    return PublicFileDTO(url=storage.generate_presigned_url(path=file.object_key))


async def confirm_uploaded_photo(*, storage: S3StorageClient, file: File) -> None:
    key = f"upload/{file.object_key}"
    content = await storage.download(path=key)

    def transform() -> bytes:
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in {"JPEG", "PNG"} or source.width * source.height > MAX_PHOTO_PIXELS:
                raise ValueError

            image = ImageOps.exif_transpose(source)

            if "A" in image.getbands() or (image.mode == "P" and "transparency" in image.info):
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")

            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85)

            return output.getvalue()

    try:
        photo = await asyncio.to_thread(transform)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidProfilePhotoError from exc

    await storage.upload(path=file.object_key, file=photo)
    await storage.delete(path=key)

    file.status = FileStatusEnum.UPLOADED.value
    file.file_size = len(photo)


async def ensure_uploaded_photo(*, storage: S3StorageClient, file: File) -> None:
    if file.status == FileStatusEnum.PENDING.value:
        await confirm_uploaded_photo(storage=storage, file=file)

    if file.status != FileStatusEnum.UPLOADED.value:
        raise ResourceNotFoundError

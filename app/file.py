import asyncio
import io

from PIL import Image, ImageOps, UnidentifiedImageError

from app.enums import AdImageKindEnum, FileStatusEnum
from app.errors import InvalidAdImageError, InvalidProfilePhotoError, ResourceNotFoundError
from app.models import File
from app.r2 import R2StorageClient
from app.schemas.base import FileDTO, PublicFileDTO

MAX_PHOTO_PIXELS = 20_000_000


def build_file_dto(*, storage: R2StorageClient, file: File | None) -> FileDTO | None:
    if file is None:
        return None

    return FileDTO(url=storage.generate_presigned_url(path=file.object_key), status=FileStatusEnum(file.status))


def build_public_file_dto(*, storage: R2StorageClient, file: File | None) -> PublicFileDTO | None:
    if file is None:
        return None

    return PublicFileDTO(url=storage.generate_presigned_url(path=file.object_key))


async def confirm_uploaded_photo(*, storage: R2StorageClient, file: File) -> None:
    key = f"upload/{file.object_key}"
    content = await storage.download(path=key)
    parts = file.file_path.split("/")
    ad_image_shape = None

    if parts[0] == "ad":
        ad_image_shape = {
            AdImageKindEnum.HOME_BANNER: (3, 1, 1200, 400),
            AdImageKindEnum.FEED: (16, 9, 1280, 720),
            AdImageKindEnum.ADVERTISER: (1, 1, 240, 240),
        }[parts[1]]

    def transform() -> bytes:
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in {"JPEG", "PNG"} or source.width * source.height > MAX_PHOTO_PIXELS:
                raise ValueError

            image = ImageOps.exif_transpose(source)

            if ad_image_shape is not None:
                ratio_width, ratio_height, min_width, min_height = ad_image_shape
                ratio_mismatch = abs(image.width * ratio_height - image.height * ratio_width)

                if image.width < min_width or image.height < min_height:
                    raise ValueError

                if ratio_mismatch > image.width * ratio_height // 100:
                    raise ValueError

            if "A" in image.getbands() or (image.mode == "P" and "transparency" in image.info):
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")

            if ad_image_shape is None:
                image.thumbnail((512, 512), Image.Resampling.LANCZOS)

            output = io.BytesIO()
            image.save(output, format="JPEG", quality=85)

            return output.getvalue()

    try:
        photo = await asyncio.to_thread(transform)
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        if ad_image_shape is not None:
            raise InvalidAdImageError from exc

        raise InvalidProfilePhotoError from exc

    await storage.upload(path=file.object_key, file=photo)
    await storage.delete(path=key)

    file.status = FileStatusEnum.UPLOADED.value
    file.file_size = len(photo)


async def ensure_uploaded_photo(*, storage: R2StorageClient, file: File) -> None:
    if file.status == FileStatusEnum.PENDING.value:
        await confirm_uploaded_photo(storage=storage, file=file)

    if file.status != FileStatusEnum.UPLOADED.value:
        raise ResourceNotFoundError

import asyncio
import io
import zipfile
from collections import defaultdict
from uuid import UUID

from app.audio_capture.domain.interfaces.repositories import IAudioSegmentRepo, ILabelCategoryRepo
from app.shared_kernel.domain.interfaces.object_storage import IObjectStorageClient


class ExportAudioSegmentsUseCase:
    def __init__(
        self,
        *,
        audio_segment_repo: IAudioSegmentRepo,
        label_category_repo: ILabelCategoryRepo,
        object_storage_client: IObjectStorageClient,
    ):
        self._audio_segment_repo = audio_segment_repo
        self._label_category_repo = label_category_repo
        self._object_storage_client = object_storage_client

    async def execute(self, *, audio_capture_label_option_ids: list[UUID] | None) -> bytes:
        audio_segments = await self._audio_segment_repo.get_labeled(
            audio_capture_label_option_ids=audio_capture_label_option_ids or []
        )
        label_categories = await self._label_category_repo.get_list()

        audio_segments_by_label_option = defaultdict(list)
        for audio_segment in audio_segments:
            audio_segments_by_label_option[audio_segment.label_option_id].append(audio_segment)

        export_folders = [
            (f"{label_category.name}/{label_option.name}", audio_segments_by_label_option[label_option.id])
            for label_category in label_categories
            for label_option in label_category.options
        ]

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for folder_path, folder_audio_segments in export_folders:
                contents = await asyncio.gather(
                    *(
                        self._object_storage_client.download(
                            path=f"{audio_segment.audio_file.file_path}/{audio_segment.audio_file.file_name}"
                        )
                        for audio_segment in folder_audio_segments
                    )
                )
                for index, content in enumerate(contents, start=1):
                    archive.writestr(f"{folder_path}/{index:03d}.wav", content)

        return buffer.getvalue()

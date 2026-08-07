from dataclasses import dataclass
from pathlib import Path

from app.shared_kernel.domain.command.file import CreateFileCommand
from app.shared_kernel.domain.exceptions import FileSizeExceededException, NotAllowedFileTypeException
from core.common.entity import Entity
from core.helpers.utils import FileSizeHelper


@dataclass(eq=False, slots=True)
class File(Entity):
    file_name: str
    file_path: str
    file_size: int
    file_type: str
    is_deleted: bool

    @classmethod
    def create(cls, *, command: CreateFileCommand) -> File:
        file = cls(
            file_name=Path(command.name).name,
            file_path=command.path,
            file_size=len(command.file),
            file_type=command.type,
            is_deleted=False,
        )
        file.file_path = f"{file.file_path}/{file.id}"
        return file

    def delete(self) -> None:
        self.is_deleted = True

    def validate(self, *, allowed_types: list[str], max_size: str | int) -> None:
        if isinstance(max_size, str):
            max_size = FileSizeHelper.convert_size_to_bytes(max_size)
            if not max_size:
                raise ValueError("Invalid size format")

        if self.file_type not in allowed_types:
            raise NotAllowedFileTypeException(
                message="허용되지 않는 파일 타입입니다. 허용된 파일 타입: {}".format(", ".join(allowed_types))
            )

        if self.file_size > max_size:
            raise FileSizeExceededException(
                message=f"최대 파일 크기를 초과했습니다."
                f" 현재 파일 크기: {FileSizeHelper.bytes_to_human_readable(self.file_size)},"
                f" 최대 크기: {FileSizeHelper.bytes_to_human_readable(max_size)}"
            )

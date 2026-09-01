from dataclasses import dataclass
from pathlib import Path
from uuid import uuid7

from app.shared_kernel.domain.commands import CreateFileCommand
from app.shared_kernel.domain.errors import FileSizeExceededError, NotAllowedFileTypeError
from core.common.entity import Entity
from core.helpers.utils import bytes_to_human_readable, convert_size_to_bytes


@dataclass(eq=False)
class File(Entity):
    file_name: str
    file_path: str
    file_size: int
    file_type: str
    is_deleted: bool

    @classmethod
    def create(cls, *, command: CreateFileCommand) -> File:
        file_id = uuid7()
        return cls(
            id=file_id,
            file_name=Path(command.name).name,
            file_path=f"{command.path}/{file_id}",
            file_size=len(command.file),
            file_type=command.type,
            is_deleted=False,
        )

    def delete(self) -> None:
        self.is_deleted = True

    def validate(self, *, allowed_types: list[str], max_size: str | int) -> None:
        if isinstance(max_size, str):
            max_size = convert_size_to_bytes(size=max_size)
            if not max_size:
                raise ValueError("Invalid size format")

        if self.file_type not in allowed_types:
            raise NotAllowedFileTypeError(
                message=f"허용되지 않는 파일 타입입니다. 허용된 파일 타입: {', '.join(allowed_types)}"
            )

        if self.file_size > max_size:
            raise FileSizeExceededError(
                message=f"최대 파일 크기를 초과했습니다."
                f" 현재 파일 크기: {bytes_to_human_readable(bytes_value=self.file_size)},"
                f" 최대 크기: {bytes_to_human_readable(bytes_value=max_size)}"
            )

from dataclasses import dataclass


@dataclass(frozen=True)
class CreateFileCommand:
    name: str
    path: str
    type: str
    file: bytes


@dataclass(frozen=True)
class AssignFileCommand:
    name: str
    type: str
    file: bytes

from dataclasses import dataclass


@dataclass
class CreateFileCommand:
    name: str
    path: str
    type: str
    file: bytes


@dataclass
class AssignFileCommand:
    name: str
    type: str
    file: bytes

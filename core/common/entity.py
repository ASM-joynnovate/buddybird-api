from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid7


@dataclass
class Entity:
    id: UUID = field(kw_only=True, default_factory=uuid7)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, type(self)):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)


class AggregateRoot(Entity):
    pass

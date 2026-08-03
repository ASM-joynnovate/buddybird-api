from abc import ABC, abstractmethod
from typing import Any


class BaseBackend(ABC):
    @abstractmethod
    async def get(self, *, key: str) -> Any:
        """Get"""

    @abstractmethod
    async def set(self, *, response: Any, key: str, ttl: int = 60) -> None:
        """Set"""

    @abstractmethod
    async def delete_include(self, *, value: str) -> None:
        """Delete include"""

    @abstractmethod
    async def delete_startwith(self, *, value: str) -> None:
        """Delete startwith"""

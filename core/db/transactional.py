import logging
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from functools import wraps
from typing import Any

from sqlalchemy.orm.exc import StaleDataError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.db.session import session

logger = logging.getLogger(__name__)

_rollback_actions: ContextVar[list[Callable[[], Awaitable[None]]]] = ContextVar("rollback_actions")


def on_rollback(action: Callable[[], Awaitable[None]]) -> None:
    if (actions := _rollback_actions.get(None)) is not None:
        actions.append(action)


class Transactional:
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        @retry(
            retry=retry_if_exception_type(StaleDataError),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
        )
        async def _transactional(*args, **kwargs) -> Any:
            token = _rollback_actions.set([])
            committed = False
            try:
                result = await func(*args, **kwargs)
                await session.commit()
                committed = True
                return result
            finally:
                if not committed:
                    for action in _rollback_actions.get():
                        try:
                            await action()
                        except Exception:
                            logger.exception("compensation failed")
                    await session.rollback()
                _rollback_actions.reset(token)

        return _transactional

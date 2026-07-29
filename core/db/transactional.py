from functools import wraps

from sqlalchemy.orm.exc import StaleDataError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .session import session


class Transactional:
    def __call__(self, func):
        @wraps(func)
        @retry(
            retry=retry_if_exception_type(StaleDataError),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
        )
        async def _transactional(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

        return _transactional

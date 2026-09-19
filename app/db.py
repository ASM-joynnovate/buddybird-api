from collections.abc import Callable
from functools import partial, wraps
from uuid import UUID

from sqlalchemy import event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria
from sqlalchemy.orm.exc import StaleDataError
from tenacity import RetryError, retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import config
from app.errors import ResourceNotFoundError
from app.models import Base

engine = create_async_engine(
    config.DB_URL,
    pool_size=10,
    max_overflow=10,
    pool_timeout=10,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=config.SQLALCHEMY_ECHO,
    hide_parameters=True,
    connect_args={"ssl": config.DB_SSL_MODE, "server_settings": {"search_path": "public"}},
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


@event.listens_for(Session, "do_orm_execute")
def exclude_soft_deleted(state: ORMExecuteState) -> None:
    if (
        state.is_select
        and state.is_orm_statement
        and not state.is_column_load
        and not state.is_relationship_load
        and not state.execution_options.get("include_deleted", False)
    ):
        state.statement = state.statement.options(
            *(
                with_loader_criteria(mapper.class_, lambda cls: cls.is_deleted.is_(False), include_aliases=True)
                for mapper in Base.registry.mappers
                if "is_deleted" in mapper.columns
            )
        )


def transactional(func: Callable | None = None, *, unavailable_error: type[Exception] | None = None) -> Callable:
    if func is None:
        return partial(transactional, unavailable_error=unavailable_error)

    @retry(
        retry=retry_if_exception_type(StaleDataError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def attempt(*args, **kwargs):
        db = kwargs["db"]
        committed = False

        try:
            result = await func(*args, **kwargs)

            await db.commit()
            committed = True

            return result
        finally:
            if not committed:
                await db.rollback()

    @wraps(func)
    async def wrapped(*args, **kwargs):
        try:
            return await attempt(*args, **kwargs)
        except (SQLAlchemyError, OSError, RetryError) as exc:
            if unavailable_error is None:
                raise

            raise unavailable_error from exc

    return wrapped


async def get_or_404[T: Base](*, db: AsyncSession, model: type[T], id: UUID) -> T:
    row = await db.scalar(select(model).where(model.id == id))

    if row is None:
        raise ResourceNotFoundError

    return row

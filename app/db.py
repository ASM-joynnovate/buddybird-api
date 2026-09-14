from collections.abc import Callable
from functools import wraps

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria
from sqlalchemy.orm.exc import StaleDataError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import config
from app.models import Base

engine = create_async_engine(
    config.DB_URL,
    pool_recycle=3600,
    echo=config.SQLALCHEMY_ECHO,
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


def transactional(func: Callable) -> Callable:
    @wraps(func)
    @retry(
        retry=retry_if_exception_type(StaleDataError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def wrapped(*args, **kwargs):
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

    return wrapped

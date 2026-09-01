from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from contextvars import ContextVar, Token
from enum import StrEnum

from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.expression import Delete, Insert, Update

from core.config import config

sqlalchemy_instrumentor = SQLAlchemyInstrumentor()

session_context: ContextVar[str] = ContextVar("session_context")


def get_session_context() -> str:
    return session_context.get()


def set_session_context(session_id: str) -> Token:
    return session_context.set(session_id)


def reset_session_context(context: Token) -> None:
    session_context.reset(context)


class EngineType(StrEnum):
    WRITER = "writer"
    READER = "reader"


engines = {
    EngineType.WRITER: create_async_engine(
        config.WRITER_DB_URL,
        pool_recycle=3600,
        echo=config.SQLALCHEMY_ECHO,
        connect_args={"ssl": config.DB_SSL_MODE},
    ),
    EngineType.READER: create_async_engine(
        config.READER_DB_URL,
        pool_recycle=3600,
        echo=config.SQLALCHEMY_ECHO,
        connect_args={"ssl": config.DB_SSL_MODE},
    ),
}


class RoutingSession(Session):
    def get_bind(self, mapper=None, clause=None, **kw) -> Engine:  # noqa: ARG002
        if self._flushing or isinstance(clause, Update | Delete | Insert):
            return engines[EngineType.WRITER].sync_engine
        return engines[EngineType.READER].sync_engine


def _is_not_deleted(cls) -> ColumnElement[bool]:
    return cls.is_deleted.is_(False)


# 모든 ORM SELECT에 is_deleted IS false를 적용
# execution_options={"include_deleted": True}로 해제
@event.listens_for(RoutingSession, "do_orm_execute")
def _exclude_soft_deleted(state: ORMExecuteState) -> None:
    from core.db.sqlalchemy.mapping.base import mapper_registry

    if (
        state.is_select
        and state.is_orm_statement
        and not state.is_column_load
        and not state.is_relationship_load
        and not state.execution_options.get("include_deleted", False)
    ):
        state.statement = state.statement.options(
            *(
                with_loader_criteria(mapper.class_, _is_not_deleted, include_aliases=True)
                for mapper in mapper_registry.mappers
                if "is_deleted" in mapper.columns
            )
        )


_async_session_factory = async_sessionmaker(
    class_=AsyncSession,
    sync_session_class=RoutingSession,
    expire_on_commit=False,
)

session = async_scoped_session(
    session_factory=_async_session_factory,
    scopefunc=get_session_context,
)


@asynccontextmanager
async def session_factory() -> AsyncGenerator[AsyncSession]:
    _session = async_sessionmaker(
        class_=AsyncSession,
        sync_session_class=RoutingSession,
        expire_on_commit=False,
    )()
    try:
        yield _session
    finally:
        await _session.close()

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from sqlalchemy import select

from app.config import config
from app.db import engine, session_factory
from app.models import UserWithdrawal
from app.oauth.base import http_client
from app.services.withdrawals import process_user_withdrawal

logger = logging.getLogger(__name__)

celery = Celery("buddybird", broker=config.CELERY_BROKER_URL)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
    broker_connection_timeout=3,
    broker_transport_options={"socket_connect_timeout": 3, "socket_timeout": 3},
    task_publish_retry=False,
    timezone="UTC",
    beat_schedule={"withdrawals-every-minute": {"task": "withdrawals.dispatch", "schedule": 60.0}},
)
runner: asyncio.Runner | None = None


@worker_process_init.connect
def initialize_worker(**_) -> None:
    global runner

    worker_runner = asyncio.Runner()
    worker_runner.run(engine.dispose(close=False))
    runner = worker_runner


@worker_process_shutdown.connect
def shutdown_worker(**_) -> None:
    global runner

    if runner is not None:
        try:
            runner.run(engine.dispose())
            runner.run(http_client.aclose())
        finally:
            runner.close()
            runner = None


def enqueue_withdrawal(*user_ids: UUID) -> None:
    for user_id in user_ids:
        try:
            process_withdrawal.delay(str(user_id))
        except Exception:
            logger.warning("탈퇴 작업 큐 전달 실패; DB 기록에서 재전달 예정")


@celery.task(name="withdrawals.process")
def process_withdrawal(user_id: str) -> None:
    if runner is None:
        raise RuntimeError("prefork worker가 필요합니다.")

    runner.run(process_user_withdrawal(UUID(user_id)))


async def dispatch_due_withdrawals() -> None:
    after = None
    due_at = datetime.now(UTC)

    while True:
        async with session_factory() as db:
            query = select(UserWithdrawal.user_id).where(
                UserWithdrawal.completed_at.is_(None), UserWithdrawal.next_attempt_at <= due_at
            )

            if after is not None:
                query = query.where(UserWithdrawal.user_id > after)

            user_ids = list((await db.scalars(query.order_by(UserWithdrawal.user_id).limit(100))).all())

        if not user_ids:
            return

        await asyncio.to_thread(enqueue_withdrawal, *user_ids)

        after = user_ids[-1]


@celery.task(name="withdrawals.dispatch")
def dispatch_withdrawals() -> None:
    if runner is None:
        raise RuntimeError("prefork worker가 필요합니다.")

    runner.run(dispatch_due_withdrawals())

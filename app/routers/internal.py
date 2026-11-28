import logging
import time
from datetime import datetime
from fnmatch import fnmatchcase
from typing import Annotated, Any
from uuid import UUID

import sentry_sdk
from fastapi import APIRouter, Header, Request

from app.db import session_factory
from app.errors import ResourceNotFoundError
from app.services import uploads
from app.services.notifications import deliver, dispatch_due_pushes, send_report
from app.services.session_sounds import (
    mark_mimic_judgment_failed,
    mark_parrot_detection_failed,
    save_mimic_judgment,
    save_parrot_detection,
)
from app.services.sessions import finish_expired_sessions
from app.services.withdrawals import dispatch_due_withdrawals, process_user_withdrawal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", include_in_schema=False)

UPLOAD_KEY_PATTERNS = ["upload/*", "user/*/word/*", "user/*/session/*", "user/*/petcam/*"]


async def confirm_upload(body: dict) -> None:
    key = body["object"]["key"]

    if not any(fnmatchcase(key, pattern) for pattern in UPLOAD_KEY_PATTERNS):
        return

    await uploads.process(key=key, size=body["object"]["size"])


async def send_notification(body: dict) -> None:
    await deliver(UUID(body["delivery_id"]))


async def process_withdrawal(body: dict) -> None:
    sentry_sdk.set_user({"id": body["user_id"]})
    sentry_sdk.set_attribute("user.id", body["user_id"])

    await process_user_withdrawal(UUID(body["user_id"]))


async def save_judgment_result(body: dict) -> None:
    async with session_factory() as db:
        if body["type"] == "audio.parrot_detected":
            session_ids = await save_parrot_detection(
                db=db,
                model_version=body["model_version"],
                analyzed_at=datetime.fromisoformat(body["analyzed_at"]),
                data=body["data"],
            )
        else:
            await save_mimic_judgment(
                db=db,
                sound_id=UUID(body["target"]["audio_id"]),
                word_id=UUID(body["reference"]["word_id"]),
                model_version=body["model_version"],
                judged_at=datetime.fromisoformat(body["analyzed_at"]),
                judgment=body["judgment"],
            )

            session_ids = [UUID(body["session_id"])]

        await send_report(db=db, session_ids=session_ids)


async def mark_parrot_sound_detection_failed(body: dict) -> None:
    async with session_factory() as db:
        await mark_parrot_detection_failed(db=db, data=body["data"])

        logger.error("앵무새 소리 판별 실패; session_id=%s data=%s", body["session_id"], body["data"])

        await send_report(db=db, session_ids=[UUID(body["session_id"])])


async def mark_mimicry_judgment_failed(body: dict) -> None:
    async with session_factory() as db:
        await mark_mimic_judgment_failed(db=db, sound_id=UUID(body["target"]["audio_id"]))

        logger.error("단어 모사 판정 실패; session_id=%s target=%s", body["session_id"], body["target"])

        await send_report(db=db, session_ids=[UUID(body["session_id"])])


QUEUE_HANDLERS = {
    "upload-confirmation": confirm_upload,
    "judgment-result": save_judgment_result,
    "notification": send_notification,
    "withdrawal": process_withdrawal,
    "parrot-sound-detection-dlq": mark_parrot_sound_detection_failed,
    "mimicry-judgment-dlq": mark_mimicry_judgment_failed,
}


@router.post("/queues/{name}")
async def consume(
    name: str,
    message: dict[str, Any],
    request: Request,
    message_id: Annotated[str, Header(alias="X-Queue-Message-Id")],
    attempts: Annotated[int, Header(alias="X-Queue-Attempts")],
    timestamp: Annotated[int, Header(alias="X-Queue-Timestamp")],
) -> None:
    handle = QUEUE_HANDLERS.get(name)

    if handle is None:
        raise ResourceNotFoundError

    enveloped = name != "upload-confirmation"
    transaction = sentry_sdk.continue_trace(message["trace"] if enveloped else {}, op="function", name=handle.__name__)

    with (
        sentry_sdk.start_transaction(transaction),
        sentry_sdk.start_span(op="queue.process", name=handle.__name__) as span,
    ):
        sentry_sdk.set_attributes({"messaging.destination.name": name, "messaging.message.id": message_id})

        span.set_data("messaging.message.id", message_id)
        span.set_data("messaging.destination.name", name)
        span.set_data("messaging.message.body.size", len(await request.body()))
        span.set_data("messaging.message.retry.count", attempts - 1)
        span.set_data("messaging.message.receive.latency", time.time() * 1000 - timestamp)

        try:
            await handle(message["body"] if enveloped else message)
        except Exception:
            logger.exception("메시지 처리 실패; queue=%s message_id=%s", name, message_id)

            raise


@router.post("/cron/{task}")
async def run(task: str) -> None:
    if task == "withdrawal.dispatch":
        await dispatch_due_withdrawals()
    elif task == "session.check_heartbeats":
        async with session_factory() as db:
            session_ids = await finish_expired_sessions(db=db)

            await send_report(db=db, session_ids=session_ids)
    elif task == "push.dispatch":
        await dispatch_due_pushes()
    else:
        raise ResourceNotFoundError

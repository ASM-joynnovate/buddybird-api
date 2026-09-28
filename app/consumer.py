import asyncio
import json
import logging
import signal
from collections.abc import Awaitable, Callable
from uuid import UUID

import sentry_sdk
from botocore.exceptions import BotoCoreError, ClientError

from app import sentry
from app.config import config
from app.services import uploads
from app.services.notifications import deliver
from app.services.withdrawals import dispatch_due_withdrawals, process_user_withdrawal
from app.sqs import get_sqs

logger = logging.getLogger(__name__)


async def confirm_upload(body: dict) -> None:
    await uploads.process(key=body["detail"]["object"]["key"], size=body["detail"]["object"]["size"])


async def send_notification(body: dict) -> None:
    await deliver(UUID(body["notification_id"]))


async def process_withdrawal(body: dict) -> None:
    sentry_sdk.set_user({"id": body["user_id"]})
    sentry_sdk.set_attribute("user.id", body["user_id"])

    await process_user_withdrawal(UUID(body["user_id"]))


async def run_periodic_command(body: dict) -> None:
    if body["type"] == "withdrawal.dispatch":
        await dispatch_due_withdrawals()


async def consume(*, queue_url: str, handle: Callable[[dict], Awaitable[None]]) -> None:
    sqs = get_sqs()

    while True:
        try:
            response = await asyncio.to_thread(
                sqs.receive_message,
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
            )
        except BotoCoreError, ClientError:
            logger.exception("메시지 수신 실패; queue_url=%s", queue_url)

            await asyncio.sleep(5)

            continue

        for message in response.get("Messages", []):
            with sentry_sdk.isolation_scope(), sentry_sdk.start_transaction(op="queue.process", name=handle.__name__):
                sentry_sdk.set_attributes(
                    {
                        "messaging.system": "aws_sqs",
                        "messaging.destination.name": queue_url.rsplit("/", 1)[-1],
                        "messaging.message.id": message["MessageId"],
                    }
                )

                try:
                    await handle(json.loads(message["Body"]))
                    await asyncio.to_thread(
                        sqs.delete_message,
                        QueueUrl=queue_url,
                        ReceiptHandle=message["ReceiptHandle"],
                    )
                except Exception:
                    logger.exception("메시지 처리 실패; queue_url=%s message_id=%s", queue_url, message["MessageId"])


async def main() -> None:
    sentry.init()

    logging.basicConfig(level=config.LOG_LEVEL)
    logging.getLogger("botocore").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)

    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, asyncio.current_task().cancel)

    try:
        await asyncio.gather(
            consume(queue_url=config.SQS_UPLOAD_CONFIRMATION_QUEUE_URL, handle=confirm_upload),
            consume(queue_url=config.SQS_NOTIFICATION_QUEUE_URL, handle=send_notification),
            consume(queue_url=config.SQS_WITHDRAWAL_QUEUE_URL, handle=process_withdrawal),
            consume(queue_url=config.SQS_PERIODIC_COMMAND_QUEUE_URL, handle=run_periodic_command),
        )
    except asyncio.CancelledError:
        logger.info("종료 신호를 받아 consumer를 종료함")


if __name__ == "__main__":
    asyncio.run(main())

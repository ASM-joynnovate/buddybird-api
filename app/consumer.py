import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError

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
    logging.basicConfig(level=config.LOG_LEVEL)
    logging.getLogger("botocore").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)

    await asyncio.gather(
        consume(queue_url=config.SQS_UPLOAD_CONFIRMATION_QUEUE_URL, handle=confirm_upload),
        consume(queue_url=config.SQS_NOTIFICATION_QUEUE_URL, handle=send_notification),
        consume(queue_url=config.SQS_WITHDRAWAL_QUEUE_URL, handle=process_withdrawal),
        consume(queue_url=config.SQS_PERIODIC_COMMAND_QUEUE_URL, handle=run_periodic_command),
    )


if __name__ == "__main__":
    asyncio.run(main())

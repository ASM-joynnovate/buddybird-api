import asyncio
import json
from functools import lru_cache
from typing import Any

import boto3
import sentry_sdk

from app.config import config


@lru_cache(maxsize=1)
def get_sqs() -> Any:
    return boto3.client(
        "sqs",
        endpoint_url=config.SQS_ENDPOINT_URL,
        aws_access_key_id=config.S3_ACCESS_KEY,
        aws_secret_access_key=config.S3_SECRET_KEY,
        region_name=config.S3_REGION,
    )


async def send(*, queue_url: str, body: dict[str, Any]) -> None:
    message = json.dumps(body)

    with sentry_sdk.start_span(op="queue.publish", name=queue_url.rsplit("/", 1)[-1]) as span:
        headers = {"sentry-trace": sentry_sdk.get_traceparent(), "baggage": sentry_sdk.get_baggage()}

        response = await asyncio.to_thread(
            get_sqs().send_message,
            QueueUrl=queue_url,
            MessageBody=message,
            MessageAttributes={
                key: {"DataType": "String", "StringValue": value} for key, value in headers.items() if value
            },
        )

        span.set_data("messaging.message.id", response["MessageId"])
        span.set_data("messaging.destination.name", queue_url.rsplit("/", 1)[-1])
        span.set_data("messaging.message.body.size", len(message.encode("utf-8")))

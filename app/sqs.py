import asyncio
import json
from functools import lru_cache
from typing import Any

import boto3

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


async def send(*, queue_url: str, body: dict[str, str]) -> None:
    await asyncio.to_thread(
        get_sqs().send_message,
        QueueUrl=queue_url,
        MessageBody=json.dumps(body),
    )

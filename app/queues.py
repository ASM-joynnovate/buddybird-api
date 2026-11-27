import json
from typing import Any

import httpx
import sentry_sdk
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_random_exponential

from app.config import config
from app.oauth.base import http_client


def is_transient(error: BaseException) -> bool:
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code == httpx.codes.TOO_MANY_REQUESTS or error.response.is_server_error

    return isinstance(error, httpx.TransportError)


@retry(retry=retry_if_exception(is_transient), stop=stop_after_attempt(5), wait=wait_random_exponential(), reraise=True)
async def publish(*, queue: str, message: dict[str, Any]) -> None:
    response = await http_client.post(f"{config.QUEUE_URL}/{queue}", json=message)
    response.raise_for_status()


async def send(*, queue: str, body: dict[str, Any]) -> None:
    with sentry_sdk.start_span(op="queue.publish", name=queue) as span:
        trace = {"sentry-trace": sentry_sdk.get_traceparent(), "baggage": sentry_sdk.get_baggage()}

        await publish(
            queue=queue, message={"body": body, "trace": {key: value for key, value in trace.items() if value}}
        )

        span.set_data("messaging.destination.name", queue)
        span.set_data("messaging.message.body.size", len(json.dumps(body).encode("utf-8")))

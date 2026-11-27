import asyncio
import base64
import logging
from typing import Any
from urllib.parse import urlsplit

import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config import config
from app.routers.internal import QUEUE_HANDLERS

API_URL = "http://localhost:8000/internal/queues"
QUEUE_PREFIX = "jn-buddybird-local-"
POLL_INTERVAL_SECONDS = 5
MAX_RETRY_INTERVAL_SECONDS = 300

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", extra="ignore")

    CLOUDFLARE_ACCOUNT_ID: str
    QUEUE_API_TOKEN: SecretStr


settings = Settings()
cloudflare = httpx.AsyncClient(
    base_url=f"https://api.cloudflare.com/client/v4/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}",
    headers={"Authorization": f"Bearer {settings.QUEUE_API_TOKEN.get_secret_value()}"},
    timeout=30,
)
api = httpx.AsyncClient(timeout=300)
queue_ids: dict[str, str] = {}
app = FastAPI()


@app.post("/{name}")
async def publish(name: str, message: dict[str, Any]) -> None:
    response = await cloudflare.post(
        f"/queues/{queue_ids[name]}/messages", json={"body": message, "content_type": "json"}
    )
    response.raise_for_status()


async def deliver(name: str) -> None:
    response = await cloudflare.post(f"/queues/{queue_ids[name]}/messages/pull", json={"batch_size": 10})
    response.raise_for_status()
    messages = response.json()["result"]["messages"]

    if not messages:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

        return

    acks = []
    retries = []

    for message in messages:
        result = await api.post(
            f"{API_URL}/{name}",
            content=base64.b64decode(message["body"]),
            headers={
                "Content-Type": "application/json",
                "X-Queue-Message-Id": message["id"],
                "X-Queue-Attempts": str(message["attempts"]),
                "X-Queue-Timestamp": str(message["timestamp_ms"]),
            },
        )

        (acks if result.is_success else retries).append({"lease_id": message["lease_id"]})

    response = await cloudflare.post(f"/queues/{queue_ids[name]}/messages/ack", json={"acks": acks, "retries": retries})
    response.raise_for_status()


async def consume(name: str) -> None:
    failures = 0

    while True:
        try:
            await deliver(name)
        except httpx.HTTPError:
            failures += 1

            logger.exception("메시지 전달 실패; queue=%s failures=%s", name, failures)

            await asyncio.sleep(min(POLL_INTERVAL_SECONDS * 2 ** (failures - 1), MAX_RETRY_INTERVAL_SECONDS))
        else:
            failures = 0


async def main() -> None:
    response = await cloudflare.get("/queues", params={"per_page": 500})
    response.raise_for_status()
    queue_ids.update(
        {
            queue["queue_name"].removeprefix(QUEUE_PREFIX): queue["queue_id"]
            for queue in response.json()["result"]
            if queue["queue_name"].startswith(QUEUE_PREFIX)
        }
    )

    server = uvicorn.Server(uvicorn.Config(app, port=urlsplit(config.QUEUE_URL).port))

    await asyncio.gather(server.serve(), *(consume(name) for name in QUEUE_HANDLERS))


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, messaging

from app.config import config


@lru_cache(maxsize=1)
def get_fcm() -> firebase_admin.App:
    if config.FCM_SERVICE_ACCOUNT_JSON is None:
        raise RuntimeError("FCM_SERVICE_ACCOUNT_JSON 설정이 필요합니다.")

    return firebase_admin.initialize_app(
        credentials.Certificate(json.loads(config.FCM_SERVICE_ACCOUNT_JSON.get_secret_value()))
    )


async def send_push(*, token: str, title: str, body: str, image_url: str | None, data: dict[str, str]) -> None:
    apns = messaging.APNSConfig(headers={"apns-priority": "10"})

    if image_url is not None:
        apns = messaging.APNSConfig(
            headers={"apns-priority": "10"},
            payload=messaging.APNSPayload(aps=messaging.Aps(mutable_content=True)),
            fcm_options=messaging.APNSFCMOptions(image=image_url),
        )

    message = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body, image=image_url),
        data=data,
        android=messaging.AndroidConfig(priority="high"),
        apns=apns,
    )

    await asyncio.to_thread(messaging.send, message, app=get_fcm())

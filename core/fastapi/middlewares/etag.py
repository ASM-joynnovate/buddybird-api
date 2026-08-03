import hashlib
from typing import NoReturn

from starlette.datastructures import Headers, MutableHeaders
from starlette.status import HTTP_200_OK, HTTP_304_NOT_MODIFIED
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class ETagMiddleware:
    def __init__(self, app: ASGIApp, minimum_size: int = 80) -> None:
        self.app = app
        self.minimum_size = minimum_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] == "GET":
            responder = ETagResponder(self.app, scope, self.minimum_size)
            await responder(scope, receive, send)
        else:
            await self.app(scope, receive, send)


class ETagResponder:
    def __init__(self, app: ASGIApp, scope: Scope, minimum_size: int) -> None:
        self.app = app
        self.scope = scope
        self.minimum_size = minimum_size
        self.send: Send = unattached_send
        self.initial_message: Message = {}
        self.headers: MutableHeaders = MutableHeaders()
        self.status_code: int | None = None
        self.delay_sending: bool = True

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self.send = send
        await self.app(scope, receive, self.send_with_etag)

    async def send_with_etag(self, message: Message) -> None:
        self._update_status_code(message)
        if not self._should_process_message():
            await self.send(message)
            return

        message_type = message["type"]
        if message_type == "http.response.start":
            await self._handle_start_message(message)
        elif message_type == "http.response.body":
            await self._handle_body_message(message)

    def _update_status_code(self, message: Message) -> None:
        if self.status_code is None:
            self.status_code = message.get("status")

    def _should_process_message(self) -> bool:
        return self.status_code == HTTP_200_OK or self.status_code == HTTP_304_NOT_MODIFIED

    async def _handle_start_message(self, message: Message) -> None:
        self.headers = MutableHeaders(raw=message["headers"])
        etag = self.headers.get("etag")

        if etag and self.compare_etag_with_if_none_match(etag):
            await self._send_not_modified(message)  # await 추가
        elif self._should_delay_for_etag():
            self.initial_message = message
        else:
            self.delay_sending = False
            await self.send(message)

    def _should_delay_for_etag(self) -> bool:
        content_length = self.headers.get("content-length")
        return bool(content_length and int(content_length) >= self.minimum_size)

    async def _send_not_modified(self, message: Message) -> None:  # async 추가
        self.status_code = message["status"] = HTTP_304_NOT_MODIFIED
        del self.headers["content-length"]
        await self.send(message)

    async def _handle_body_message(self, message: Message) -> None:
        if not self.delay_sending:
            await self.send(message)
            return

        body = message.get("body", b"")
        if len(body) >= self.minimum_size:
            self._process_etag(body, message)
            await self.send(self.initial_message)
        await self.send(message)

    def _process_etag(self, body: bytes, message: Message) -> None:
        etag = hashlib.sha256(body).hexdigest()
        self.headers["etag"] = etag
        if self.compare_etag_with_if_none_match(etag):
            del self.headers["content-length"]
            self.initial_message["status"] = HTTP_304_NOT_MODIFIED
            message["body"] = b""

    def compare_etag_with_if_none_match(self, etag: str) -> bool:
        if_none_match = Headers(scope=self.scope).get("if-none-match")
        if if_none_match:
            if_none_match = if_none_match.removeprefix("W/")
            return if_none_match == etag
        return False


async def unattached_send(_message: Message) -> NoReturn:
    raise RuntimeError("send awaitable not set")  # pragma: no cover

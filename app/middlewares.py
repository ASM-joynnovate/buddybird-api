import hashlib
from dataclasses import dataclass, field
from uuid import UUID

from starlette.authentication import AuthCredentials, AuthenticationBackend, BaseUser
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import HTTPConnection
from starlette.status import HTTP_200_OK, HTTP_304_NOT_MODIFIED
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import AuthenticationError, AuthenticationServiceUnavailableError
from app.oauth.supabase import verify_access_token


class ETagMiddleware:
    def __init__(self, app: ASGIApp, minimum_size: int = 80):
        self.app = app
        self.minimum_size = minimum_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "GET"
            or scope["path"].startswith(("/api/v1/auth/", "/api/v1/users/", "/api/v1/backoffice/exports/"))
        ):
            await self.app(scope, receive, send)
            return

        if_none_match = Headers(scope=scope).get("if-none-match", "").removeprefix("W/")
        initial_message: Message | None = None

        async def send_with_etag(message: Message) -> None:
            nonlocal initial_message

            if message["type"] == "http.response.start":
                initial_message = message
                return

            if initial_message is None:
                await send(message)
                return

            headers = MutableHeaders(raw=initial_message["headers"])
            body = message.get("body", b"")
            etag = headers.get("etag")
            content_length = int(headers.get("content-length", "0"))
            is_ok = initial_message["status"] == HTTP_200_OK

            if is_ok and etag != if_none_match and min(content_length, len(body)) >= self.minimum_size:
                etag = hashlib.sha256(body).hexdigest()
                headers["etag"] = etag

            if is_ok and etag and if_none_match == etag:
                initial_message["status"] = HTTP_304_NOT_MODIFIED
                del headers["content-length"]
                message["body"] = b""

            await send(initial_message)
            initial_message = None

            await send(message)

        await self.app(scope, receive, send_with_etag)


class NoStoreMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(("/api/v1/auth/", "/api/v1/users/")):
            await self.app(scope, receive, send)
            return

        async def send_no_store(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message["headers"])
                headers["cache-control"] = "no-store"
                if "etag" in headers:
                    del headers["etag"]
            await send(message)

        await self.app(scope, receive, send_no_store)


@dataclass(frozen=True)
class AuthContext(BaseUser):
    auth_user_id: UUID
    access_token: str = field(repr=False)

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return str(self.auth_user_id)

    @property
    def identity(self) -> str:
        return str(self.auth_user_id)


class AuthBackend(AuthenticationBackend):
    async def authenticate(self, conn: HTTPConnection) -> tuple[AuthCredentials, BaseUser] | None:
        authorization = conn.headers.get("Authorization")

        if authorization is None:
            return None

        scheme, _, token = authorization.partition(" ")
        token = token.strip()

        if scheme.lower() != "bearer" or not token:
            conn.scope.setdefault("state", {})["auth_error"] = AuthenticationError()

            return None

        try:
            auth_user_id = await verify_access_token(token)
        except (AuthenticationError, AuthenticationServiceUnavailableError) as exc:
            conn.scope.setdefault("state", {})["auth_error"] = exc

            return None

        return AuthCredentials(["authenticated"]), AuthContext(auth_user_id=auth_user_id, access_token=token)

import logging
import secrets
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from starlette.authentication import AuthCredentials, AuthenticationBackend, BaseUser
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import config
from app.db import session_factory
from app.errors import AuthenticationError, AuthenticationServiceUnavailableError, IdempotencyKeyRequiredError
from app.models import ProcessedRequest, User
from app.oauth.supabase import verify_access_token

logger = logging.getLogger(__name__)


class NoStoreMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_no_store(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(raw=message["headers"]).setdefault("cache-control", "no-store")

            await send(message)

        await self.app(scope, receive, send_no_store)


@dataclass(frozen=True)
class AuthContext(BaseUser):
    auth_user_id: UUID
    access_token: str = field(repr=False)
    is_anonymous: bool

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return str(self.auth_user_id)

    @property
    def identity(self) -> str:
        return str(self.auth_user_id)


class IdempotencyMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH", "DELETE"}:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        backoffice_authorized = scope["path"].startswith(
            (
                "/api/v1/backoffice/announcements",
                "/api/v1/backoffice/app-updates",
                "/api/v1/backoffice/consents",
                "/api/v1/backoffice/notifications",
                "/api/v1/backoffice/preset-words",
                "/api/v1/backoffice/users",
            )
        ) and secrets.compare_digest(
            headers.get("x-backoffice-password", "").encode(), config.BACKOFFICE_PASSWORD.encode()
        )

        if not backoffice_authorized and (
            not scope["path"].startswith(
                (
                    "/api/v1/users/me/settings",
                    "/api/v1/users/me/consents",
                    "/api/v1/devices",
                    "/api/v1/parrots",
                    "/api/v1/words",
                    "/api/v1/sessions",
                    "/api/v1/feedback",
                    "/api/v1/announcements",
                    "/api/v1/notifications",
                )
            )
            or not isinstance(scope.get("user"), AuthContext)
        ):
            await self.app(scope, receive, send)
            return

        try:
            request_id = UUID(headers.get("idempotency-key", ""))
        except ValueError:
            error = IdempotencyKeyRequiredError()
            response = JSONResponse(
                status_code=error.status_code, content={"error_code": error.error_code, "message": error.message}
            )
            await response(scope, receive, send)
            return

        async with session_factory() as db:
            user_id = (
                None
                if backoffice_authorized
                else await db.scalar(select(User.id).where(User.auth_user_id == scope["user"].auth_user_id))
            )
            processed = None

            if backoffice_authorized or user_id is not None:
                processed = await db.scalar(
                    select(ProcessedRequest).where(
                        ProcessedRequest.user_id == user_id, ProcessedRequest.request_id == request_id
                    )
                )

        if not backoffice_authorized and user_id is None:
            await self.app(scope, receive, send)
            return

        if processed is not None:
            response = Response(
                content=processed.response_body,
                status_code=processed.response_status,
                media_type="application/json",
            )
            await response(scope, receive, send)
            return

        status_code: int | None = None
        chunks: list[bytes] = []

        async def send_and_record(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                chunks.append(message.get("body", b""))

            await send(message)

        await self.app(scope, receive, send_and_record)

        if status_code is None or status_code >= 500:
            return

        try:
            async with session_factory() as db:
                await db.execute(
                    insert(ProcessedRequest)
                    .values(
                        user_id=user_id,
                        request_id=request_id,
                        response_status=status_code,
                        response_body=b"".join(chunks).decode(),
                    )
                    .on_conflict_do_nothing(index_elements=[ProcessedRequest.user_id, ProcessedRequest.request_id])
                )
                await db.commit()
        except SQLAlchemyError, OSError:
            logger.exception("중복 방지 기록 저장 실패")


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
            auth_user_id, is_anonymous = await verify_access_token(token)
        except (AuthenticationError, AuthenticationServiceUnavailableError) as exc:
            conn.scope.setdefault("state", {})["auth_error"] = exc

            return None

        return AuthCredentials(["authenticated"]), AuthContext(
            auth_user_id=auth_user_id, access_token=token, is_anonymous=is_anonymous
        )

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid7

import httpx
import jwt
from botocore.exceptions import BotoCoreError, ClientError
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientConnectionError, PyJWKClientError, PyJWKSetError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.authentication import AuthCredentials, AuthenticationBackend, BaseUser
from starlette.requests import HTTPConnection

from app.config import config
from app.db import session_factory
from app.errors import AuthenticationError, AuthenticationServiceUnavailableError, UserSaveUnavailableError
from app.models import File, User
from app.s3 import S3StorageClient
from app.schemas import LoginDTO
from app.users import delete_uploaded_photo, download_social_photo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthContext(BaseUser):
    auth_user_id: UUID
    access_token: str
    user_id: UUID | None = None
    is_deleted: bool = False

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return str(self.user_id or self.auth_user_id)

    @property
    def identity(self) -> str:
        return str(self.auth_user_id)


class SupabaseTokenVerifier:
    def __init__(self) -> None:
        self._issuer = f"{config.SUPABASE_URL.rstrip('/')}/auth/v1" if config.SUPABASE_URL else None
        self._jwks = (
            PyJWKClient(f"{self._issuer}/.well-known/jwks.json", cache_jwk_set=True, lifespan=300, timeout=5)
            if self._issuer
            else None
        )

    async def verify(self, token: str) -> UUID:
        if self._jwks is None or self._issuer is None:
            raise AuthenticationServiceUnavailableError
        try:
            key = await asyncio.to_thread(self._jwks.get_signing_key_from_jwt, token)
        except (PyJWKClientConnectionError, PyJWKSetError, OSError, TimeoutError) as exc:
            raise AuthenticationServiceUnavailableError from exc
        except (InvalidTokenError, PyJWKClientError, TypeError, ValueError) as exc:
            raise AuthenticationError from exc
        try:
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256", "ES256"],
                audience=config.SUPABASE_AUDIENCE,
                issuer=self._issuer,
                options={"require": ["iss", "aud", "exp", "iat", "sub", "role", "session_id", "is_anonymous"]},
            )
            auth_user_id = UUID(claims["sub"])
            UUID(claims["session_id"])
        except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError from exc
        if claims.get("role") != "authenticated" or claims.get("is_anonymous") is not False:
            raise AuthenticationError
        return auth_user_id


class AuthBackend(AuthenticationBackend):
    def __init__(self) -> None:
        self._verifier = SupabaseTokenVerifier()

    async def authenticate(self, conn: HTTPConnection) -> tuple[AuthCredentials, BaseUser] | None:
        authorization = conn.headers.get("Authorization")
        if authorization is None:
            return None
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            conn.scope.setdefault("state", {})["auth_error"] = AuthenticationError()
            return None
        try:
            auth_user_id = await self._verifier.verify(token.strip())
            async with session_factory() as db:
                row = (
                    await db.execute(
                        select(User.id, User.is_deleted)
                        .where(User.auth_user_id == auth_user_id)
                        .execution_options(use_writer=True, include_deleted=True)
                    )
                ).one_or_none()
        except (AuthenticationError, AuthenticationServiceUnavailableError) as exc:
            conn.scope.setdefault("state", {})["auth_error"] = exc
            return None
        except SQLAlchemyError as exc:
            conn.scope.setdefault("state", {})["auth_error"] = AuthenticationServiceUnavailableError()
            logger.warning("인증 사용자 조회 실패", exc_info=exc)
            return None
        context = AuthContext(
            auth_user_id=auth_user_id,
            access_token=token.strip(),
            user_id=row.id if row else None,
            is_deleted=row.is_deleted if row else False,
        )
        return AuthCredentials(["authenticated"]), context


async def get_social_profile(*, auth_user_id: UUID, access_token: str) -> tuple[str, str | None, str | None]:
    if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
        raise AuthenticationServiceUnavailableError
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
            response = await client.get(
                f"{config.SUPABASE_URL.rstrip('/')}/auth/v1/user",
                headers={"Authorization": f"Bearer {access_token}", "apikey": config.SUPABASE_ANON_KEY},
            )
    except httpx.HTTPError as exc:
        raise AuthenticationServiceUnavailableError from exc
    if response.status_code in {401, 403}:
        raise AuthenticationError
    try:
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise AuthenticationServiceUnavailableError from exc
    try:
        if data["id"] != str(auth_user_id):
            raise AuthenticationServiceUnavailableError
        identities = [
            identity for identity in data["identities"] if identity["provider"] in {"google", "apple", "kakao"}
        ]
    except (KeyError, TypeError) as exc:
        raise AuthenticationServiceUnavailableError from exc
    if not identities:
        raise AuthenticationError
    try:
        identity = min(
            identities,
            key=lambda item: (datetime.fromisoformat(item["created_at"]), item["identity_id"]),
        )
        profile = identity["identity_data"]
        email = profile.get("email")
        photo_url = profile.get("avatar_url") or profile.get("picture")
        return (
            identity["provider"],
            email if isinstance(email, str) else None,
            photo_url if isinstance(photo_url, str) else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthenticationServiceUnavailableError from exc


async def complete_login(*, context: AuthContext, db, storage: S3StorageClient) -> LoginDTO:
    if context.is_deleted:
        raise AuthenticationError
    if context.user_id is not None:
        return LoginDTO(user_id=context.user_id, is_new_user=False)

    provider, email, photo_url = await get_social_profile(
        auth_user_id=context.auth_user_id,
        access_token=context.access_token,
    )
    user_id = uuid7()
    uploaded_path = None
    photo_file = None
    if photo_url and (photo := await download_social_photo(url=photo_url, provider=provider)):
        content, file_name, file_type = photo
        file_id = uuid7()
        file_path = f"user/{user_id}/profile/{file_id}"
        uploaded_path = f"{file_path}/{file_name}"
        try:
            await storage.upload(path=uploaded_path, file=content)
        except BotoCoreError, ClientError, OSError, TimeoutError:
            uploaded_path = None
        else:
            photo_file = File(
                id=file_id,
                file_name=file_name,
                file_path=file_path,
                file_size=len(content),
                file_type=file_type,
                is_deleted=False,
            )

    user = User(
        id=user_id,
        auth_user_id=context.auth_user_id,
        email=email,
        nickname=None,
        photo_file=photo_file,
        is_deleted=False,
    )
    db.add(user)
    try:
        await db.flush()
    except SQLAlchemyError as exc:
        try:
            await db.rollback()
        except SQLAlchemyError as rollback_exc:
            raise UserSaveUnavailableError from rollback_exc
        if uploaded_path:
            await delete_uploaded_photo(storage=storage, path=uploaded_path)
        if isinstance(exc, IntegrityError):
            async with session_factory() as check_db:
                existing = (
                    await check_db.execute(
                        select(User.id, User.is_deleted)
                        .where(User.auth_user_id == context.auth_user_id)
                        .execution_options(use_writer=True, include_deleted=True)
                    )
                ).one_or_none()
            if existing is not None:
                if existing.is_deleted:
                    raise AuthenticationError from exc
                return LoginDTO(user_id=existing.id, is_new_user=False)
        raise UserSaveUnavailableError from exc
    try:
        await db.commit()
    except SQLAlchemyError as exc:
        with suppress(SQLAlchemyError):
            await db.rollback()
        async with session_factory() as check_db:
            existing = (
                await check_db.execute(
                    select(User.id, User.is_deleted)
                    .where(User.auth_user_id == context.auth_user_id)
                    .execution_options(use_writer=True, include_deleted=True)
                )
            ).one_or_none()
        if existing is not None:
            if existing.is_deleted:
                raise AuthenticationError from exc
            return LoginDTO(user_id=existing.id, is_new_user=existing.id == user_id)
        raise UserSaveUnavailableError from exc
    return LoginDTO(user_id=user_id, is_new_user=True)

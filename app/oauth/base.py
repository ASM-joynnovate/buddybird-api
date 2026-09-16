import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Literal
from uuid import UUID

import httpx
from cryptography.fernet import Fernet, InvalidToken
from jwt import PyJWKClient

from app.config import config
from app.errors import OAuthCredentialError, WithdrawalOperationError
from app.models import OAuthProviderEnum

http_client = httpx.AsyncClient(timeout=10, follow_redirects=False)


@dataclass(frozen=True)
class SocialIdentity:
    identity_id: UUID
    provider: OAuthProviderEnum
    subject: str
    created_at: datetime
    email: str | None
    photo_url: str | None


def credential_cipher() -> Fernet:
    if config.OAUTH_CREDENTIALS_KEY is None:
        raise WithdrawalOperationError("credentials_key_missing")

    try:
        return Fernet(config.OAUTH_CREDENTIALS_KEY.get_secret_value().encode())
    except ValueError:
        raise WithdrawalOperationError("credentials_key_invalid") from None


def encrypt_credentials(data: dict | list) -> str:
    return credential_cipher().encrypt(json.dumps(data).encode()).decode()


def decrypt_credentials(ciphertext: str) -> dict | list:
    try:
        return json.loads(credential_cipher().decrypt(ciphertext.encode()))
    except InvalidToken, ValueError, TypeError:
        raise WithdrawalOperationError("credentials_unreadable") from None


@lru_cache
def jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_jwk_set=True, lifespan=300, timeout=5)


async def provider_request(
    method: str, url: str, *, provider: OAuthProviderEnum | Literal["supabase"], **kwargs
) -> httpx.Response:
    try:
        response = await http_client.request(method, url, **kwargs)
    except httpx.HTTPError:
        raise WithdrawalOperationError(f"{provider}_unavailable", retryable=True) from None

    if response.status_code in {408, 429} or response.status_code >= 500:
        raise WithdrawalOperationError(f"{provider}_unavailable", retryable=True)

    return response


def response_object(response: httpx.Response, *, provider: OAuthProviderEnum | Literal["supabase"]) -> dict:
    try:
        data = response.json()
    except ValueError:
        raise WithdrawalOperationError(f"{provider}_invalid_response", retryable=response.status_code == 200) from None

    if not isinstance(data, dict):
        raise WithdrawalOperationError(f"{provider}_invalid_response", retryable=response.status_code == 200)

    return data


def match_identity(*, identities: list[SocialIdentity], provider: OAuthProviderEnum, subject: str) -> SocialIdentity:
    matches = [item for item in identities if item.provider == provider and item.subject == subject]

    if len(matches) != 1:
        raise OAuthCredentialError

    return matches[0]


def token_response(response: httpx.Response, *, provider: OAuthProviderEnum) -> dict:
    data = response_object(response, provider=provider)

    if response.status_code == 400 and data.get("error") == "invalid_grant":
        raise OAuthCredentialError

    if response.status_code != 200 or "error" in data:
        raise WithdrawalOperationError(f"{provider}_token_rejected")

    return data

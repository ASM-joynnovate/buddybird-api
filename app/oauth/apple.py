import asyncio
from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError, PyJWKClientConnectionError, PyJWKClientError, PyJWKSetError

from app.config import config
from app.enums import OAuthProviderEnum
from app.errors import OAuthCredentialError, WithdrawalOperationError
from app.oauth.base import SocialIdentity, jwks_client, match_identity, provider_request, token_response


def apple_client_secret(client_id: str) -> str:
    if client_id not in config.APPLE_CLIENT_IDS:
        raise WithdrawalOperationError("apple_client_not_allowed")

    if not config.APPLE_TEAM_ID or not config.APPLE_KEY_ID or not config.APPLE_PRIVATE_KEY:
        raise WithdrawalOperationError("apple_configuration_missing")

    now = datetime.now(UTC)

    try:
        return jwt.encode(
            {
                "iss": config.APPLE_TEAM_ID,
                "sub": client_id,
                "aud": "https://appleid.apple.com",
                "iat": now,
                "exp": now + timedelta(minutes=5),
            },
            config.APPLE_PRIVATE_KEY.get_secret_value(),
            algorithm="ES256",
            headers={"kid": config.APPLE_KEY_ID},
        )
    except ValueError, TypeError, jwt.PyJWTError:
        raise WithdrawalOperationError("apple_signing_key_invalid") from None


async def verify_apple_credential(
    *, client_id: str, authorization_code: str, identities: list[SocialIdentity]
) -> tuple[SocialIdentity, str]:
    if client_id not in config.APPLE_CLIENT_IDS:
        raise OAuthCredentialError

    response = await provider_request(
        "POST",
        "https://appleid.apple.com/auth/token",
        provider=OAuthProviderEnum.APPLE,
        data={
            "grant_type": "authorization_code",
            "code": authorization_code,
            "client_id": client_id,
            "client_secret": apple_client_secret(client_id),
        },
    )
    tokens = token_response(response, provider=OAuthProviderEnum.APPLE)
    refresh_token = tokens.get("refresh_token")
    id_token = tokens.get("id_token")

    if not isinstance(refresh_token, str) or not refresh_token or not isinstance(id_token, str):
        raise WithdrawalOperationError("apple_invalid_response", retryable=True)

    try:
        key = await asyncio.to_thread(
            jwks_client("https://appleid.apple.com/auth/keys").get_signing_key_from_jwt, id_token
        )
        claims = jwt.decode(
            id_token,
            key.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer="https://appleid.apple.com",
            options={"require": ["iss", "aud", "exp", "iat", "sub"]},
        )
    except PyJWKClientConnectionError, PyJWKSetError, OSError, TimeoutError:
        raise WithdrawalOperationError("apple_keys_unavailable", retryable=True) from None
    except InvalidTokenError, PyJWKClientError, TypeError, ValueError:
        raise OAuthCredentialError from None

    identity = match_identity(identities=identities, provider=OAuthProviderEnum.APPLE, subject=claims["sub"])

    return identity, refresh_token


async def revoke_apple(*, client_id: str, refresh_token: str) -> None:
    response = await provider_request(
        "POST",
        "https://appleid.apple.com/auth/revoke",
        provider=OAuthProviderEnum.APPLE,
        data={
            "client_id": client_id,
            "client_secret": apple_client_secret(client_id),
            "token": refresh_token,
            "token_type_hint": "refresh_token",
        },
    )

    if response.status_code != 200 or response.content.strip():
        raise WithdrawalOperationError("apple_revoke_rejected")

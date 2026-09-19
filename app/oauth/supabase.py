import asyncio
from datetime import datetime
from uuid import UUID

import jwt
from jwt.exceptions import InvalidTokenError, PyJWKClientConnectionError, PyJWKClientError, PyJWKSetError

from app.config import config
from app.enums import OAuthProviderEnum
from app.errors import AuthenticationError, AuthenticationServiceUnavailableError, WithdrawalOperationError
from app.oauth.base import SocialIdentity, jwks_client, provider_request, response_object


async def verify_access_token(token: str) -> UUID:
    issuer = config.SUPABASE_AUTH_URL

    if issuer is None:
        raise AuthenticationServiceUnavailableError

    try:
        key = await asyncio.to_thread(jwks_client(f"{issuer}/.well-known/jwks.json").get_signing_key_from_jwt, token)
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
            issuer=issuer,
            options={"require": ["iss", "aud", "exp", "iat", "sub", "role", "session_id", "is_anonymous"]},
        )
        auth_user_id = UUID(claims["sub"])
        UUID(claims["session_id"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError from exc

    if claims.get("role") != "authenticated" or claims.get("is_anonymous") is not False:
        raise AuthenticationError

    return auth_user_id


async def get_social_identities(*, auth_user_id: UUID, access_token: str) -> list[SocialIdentity]:
    if config.SUPABASE_AUTH_URL is None or not config.SUPABASE_PUBLISHABLE_KEY:
        raise AuthenticationServiceUnavailableError

    try:
        response = await provider_request(
            "GET",
            f"{config.SUPABASE_AUTH_URL}/user",
            provider="supabase",
            headers={"Authorization": f"Bearer {access_token}", "apikey": config.SUPABASE_PUBLISHABLE_KEY},
        )
    except WithdrawalOperationError:
        raise AuthenticationServiceUnavailableError from None

    if response.status_code in {401, 403}:
        raise AuthenticationError

    if response.status_code != 200:
        raise AuthenticationServiceUnavailableError

    identities = []

    try:
        data = response_object(response, provider="supabase")

        if data["id"] != str(auth_user_id):
            raise AuthenticationServiceUnavailableError

        for item in data["identities"]:
            if item["provider"] not in OAuthProviderEnum:
                continue

            if item["user_id"] != str(auth_user_id) or not isinstance(item["id"], str) or not item["id"]:
                raise AuthenticationServiceUnavailableError

            profile = item["identity_data"]
            email = profile.get("email")
            photo_url = profile.get("avatar_url") or profile.get("picture")

            identities.append(
                SocialIdentity(
                    identity_id=UUID(item["identity_id"]),
                    provider=OAuthProviderEnum(item["provider"]),
                    subject=item["id"],
                    created_at=datetime.fromisoformat(item["created_at"]),
                    email=email if isinstance(email, str) else None,
                    photo_url=photo_url if isinstance(photo_url, str) else None,
                )
            )
    except WithdrawalOperationError, KeyError, TypeError, ValueError, AttributeError:
        raise AuthenticationServiceUnavailableError from None

    if not identities:
        raise AuthenticationError

    return identities


async def delete_supabase_user(auth_user_id: UUID) -> None:
    if config.SUPABASE_AUTH_URL is None or not config.SUPABASE_SECRET_KEY:
        raise WithdrawalOperationError("supabase_admin_configuration_missing")

    key = config.SUPABASE_SECRET_KEY.get_secret_value()
    url = f"{config.SUPABASE_AUTH_URL}/admin/users/{auth_user_id}"
    headers = {"Authorization": f"Bearer {key}", "apikey": key}

    response = await provider_request("GET", url, provider="supabase", headers=headers)
    data = response_object(response, provider="supabase")

    if response.status_code == 404 and data.get("error_code") == "user_not_found":
        return

    if response.status_code != 200 or data.get("id") != str(auth_user_id):
        raise WithdrawalOperationError("supabase_user_lookup_rejected")

    response = await provider_request(
        "DELETE", url, provider="supabase", headers=headers, json={"should_soft_delete": False}
    )
    data = response_object(response, provider="supabase")

    if response.status_code == 404 and data.get("error_code") == "user_not_found":
        return

    if response.status_code != 200 or data != {}:
        raise WithdrawalOperationError("supabase_delete_rejected")

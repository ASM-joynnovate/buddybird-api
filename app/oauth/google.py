from app.config import config
from app.errors import OAuthCredentialError, WithdrawalOperationError
from app.models import OAuthProviderEnum, WithdrawalStatusEnum
from app.oauth.base import SocialIdentity, match_identity, provider_request, response_object, token_response


async def verify_google_credential(
    *, refresh_token: str, identities: list[SocialIdentity]
) -> tuple[SocialIdentity, str]:
    if not config.GOOGLE_CLIENT_ID or not config.GOOGLE_CLIENT_SECRET:
        raise WithdrawalOperationError("google_configuration_missing")

    response = await provider_request(
        "POST",
        "https://oauth2.googleapis.com/token",
        provider=OAuthProviderEnum.GOOGLE,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET.get_secret_value(),
        },
    )
    tokens = token_response(response, provider=OAuthProviderEnum.GOOGLE)
    access_token = tokens.get("access_token")

    if not isinstance(access_token, str) or not access_token:
        raise WithdrawalOperationError("google_invalid_response", retryable=True)

    response = await provider_request(
        "GET",
        "https://openidconnect.googleapis.com/v1/userinfo",
        provider=OAuthProviderEnum.GOOGLE,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    if response.status_code != 200:
        raise OAuthCredentialError

    subject = response_object(response, provider=OAuthProviderEnum.GOOGLE).get("sub")

    if not isinstance(subject, str) or not subject:
        raise OAuthCredentialError

    identity = match_identity(identities=identities, provider=OAuthProviderEnum.GOOGLE, subject=subject)
    token = tokens.get("refresh_token", refresh_token)

    if not isinstance(token, str) or not token:
        raise WithdrawalOperationError("google_invalid_response", retryable=True)

    return identity, token


async def revoke_google(refresh_token: str) -> WithdrawalStatusEnum:
    response = await provider_request(
        "POST", "https://oauth2.googleapis.com/revoke", provider=OAuthProviderEnum.GOOGLE, data={"token": refresh_token}
    )

    if response.status_code == 200:
        if response.content.strip():
            raise WithdrawalOperationError("google_invalid_response", retryable=True)

        return WithdrawalStatusEnum.COMPLETED

    if (
        response.status_code == 400
        and response_object(response, provider=OAuthProviderEnum.GOOGLE).get("error") == "invalid_token"
    ):
        return WithdrawalStatusEnum.UNCONFIRMED

    raise WithdrawalOperationError("google_revoke_rejected")

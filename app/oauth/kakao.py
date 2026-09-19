from app.config import config
from app.enums import OAuthProviderEnum
from app.errors import WithdrawalOperationError
from app.oauth.base import provider_request, response_object


async def unlink_kakao(user_id: str) -> None:
    if not config.KAKAO_ADMIN_KEY:
        raise WithdrawalOperationError("kakao_configuration_missing")

    response = await provider_request(
        "POST",
        "https://kapi.kakao.com/v1/user/unlink",
        provider=OAuthProviderEnum.KAKAO,
        headers={"Authorization": f"KakaoAK {config.KAKAO_ADMIN_KEY.get_secret_value()}"},
        data={"target_id_type": "user_id", "target_id": user_id},
    )
    data = response_object(response, provider=OAuthProviderEnum.KAKAO)

    if response.status_code == 200 and type(data.get("id")) is int and str(data["id"]) == user_id:
        return

    if response.status_code == 400 and data.get("code") == -101:
        return

    if data.get("code") in {-1, -10}:
        raise WithdrawalOperationError("kakao_unavailable", retryable=True)

    raise WithdrawalOperationError("kakao_unlink_rejected")

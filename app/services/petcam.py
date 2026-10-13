import logging

import httpx

from app.config import config
from app.errors import PetcamTurnUnavailableError
from app.oauth.base import http_client
from app.schemas.petcam import IceServerDTO, TurnCredentialDTO

logger = logging.getLogger(__name__)

TURN_CREDENTIAL_TTL_SECONDS = 86400


async def issue_turn_credential() -> TurnCredentialDTO:
    if config.CLOUDFLARE_TURN_KEY_ID is None or config.CLOUDFLARE_TURN_API_TOKEN is None:
        raise PetcamTurnUnavailableError

    try:
        response = await http_client.post(
            "https://rtc.live.cloudflare.com/v1/turn/keys/"
            f"{config.CLOUDFLARE_TURN_KEY_ID}/credentials/generate-ice-servers",
            headers={"Authorization": f"Bearer {config.CLOUDFLARE_TURN_API_TOKEN.get_secret_value()}"},
            json={"ttl": TURN_CREDENTIAL_TTL_SECONDS},
        )
    except httpx.HTTPError as exc:
        logger.exception("Cloudflare TURN 접속 정보 발급 실패")

        raise PetcamTurnUnavailableError from exc

    if not response.is_success:
        logger.error("Cloudflare TURN 접속 정보 발급 실패: %s %s", response.status_code, response.text)

        raise PetcamTurnUnavailableError

    return TurnCredentialDTO(
        ice_servers=[
            IceServerDTO(urls=server["urls"], username=server.get("username"), credential=server.get("credential"))
            for server in response.json()["iceServers"]
        ]
    )

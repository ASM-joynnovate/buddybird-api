from datetime import UTC, datetime, timedelta
from json import JSONEncoder
from typing import Any
from uuid import UUID

import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError

from core.common.errors import CustomError
from core.config import config


class DecodeTokenError(CustomError):
    code = 400
    error_code = "COMMON__TOKEN_DECODE_ERROR"
    message = "유효하지 않은 토큰입니다."


class ExpiredTokenError(CustomError):
    code = 400
    error_code = "COMMON__TOKEN_EXPIRE_TOKEN"
    message = "만료된 토큰입니다."


class UUIDEncoder(JSONEncoder):
    def default(self, obj) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        return JSONEncoder.default(self, obj)


def encode_token(*, payload: dict, key: str, delta: int) -> tuple[str, float]:
    exp = (datetime.now(tz=UTC) + timedelta(minutes=delta)).timestamp()
    token = jwt.encode(
        payload={
            **payload,
            "exp": exp,
        },
        key=key,
        algorithm=config.AUTH_ALGORITHM,
        json_encoder=UUIDEncoder,
    )

    return token, exp


def decode_token(*, token: str, key: str) -> dict:
    try:
        return jwt.decode(
            token,
            key,
            config.AUTH_ALGORITHM,
            verify=True,
        )
    except DecodeError as e:
        raise DecodeTokenError from e
    except ExpiredSignatureError as e:
        raise ExpiredTokenError from e

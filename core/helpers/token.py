from datetime import datetime, timedelta
from json import JSONEncoder
from uuid import UUID

import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError

from core.common.exceptions import CustomException
from core.config import config


class DecodeTokenException(CustomException):
    code = 400
    error_code = "TOKEN__DECODE_ERROR"
    message = "유효하지 않은 토큰입니다."


class ExpiredTokenException(CustomException):
    code = 400
    error_code = "TOKEN__EXPIRE_TOKEN"
    message = "만료된 토큰입니다."


class UUIDEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return JSONEncoder.default(self, obj)


class TokenHelper:
    @staticmethod
    def encode(
            *,
            payload: dict,
            key: str,
            delta: int,
    ) -> tuple[str, float]:
        exp = (datetime.now() + timedelta(minutes=delta)).timestamp()
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

    @staticmethod
    def decode(token: str, key: str) -> dict:
        try:
            return jwt.decode(
                token,
                key,
                config.AUTH_ALGORITHM,
                verify=True,
            )
        except DecodeError as e:
            raise DecodeTokenException from e
        except ExpiredSignatureError as e:
            raise ExpiredTokenException from e

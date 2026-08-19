from app.word.application.dto import GetWordDTO
from core.common.response import BaseResponse


class GetWordListResponse(BaseResponse):
    data: list[GetWordDTO]


class GetWordResponse(BaseResponse):
    data: GetWordDTO

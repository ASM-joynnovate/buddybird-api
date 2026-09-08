from app.legacy.audio_capture.application.dto import GetLabelCategoryDTO
from core.common.response import BaseResponse


class GetLabelListResponse(BaseResponse):
    data: list[GetLabelCategoryDTO]

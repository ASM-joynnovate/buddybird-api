from app.audio_capture.application.dto.label import GetLabelCategoryDTO
from core.common.response import BaseResponse


class GetLabelListResponse(BaseResponse):
    data: list[GetLabelCategoryDTO]

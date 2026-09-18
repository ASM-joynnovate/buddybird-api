from fastapi import APIRouter

from app.dependencies import ActiveDevice, ActiveUser, DBSession
from app.schemas.base import BaseResponse
from app.schemas.devices import (
    DeviceListResponse,
    DeviceResponse,
    RegisterDeviceRequest,
    UpdateDeviceRequest,
    UpdatePushTokenRequest,
)
from app.services import devices

router = APIRouter(prefix="/devices")


@router.put("", name="기기 등록", response_model=DeviceResponse)
async def register(user: ActiveUser, body: RegisterDeviceRequest, db: DBSession) -> DeviceResponse:
    return DeviceResponse(message="기기 등록 성공", data=await devices.register(db=db, user=user, data=body))


@router.get("", name="기기 목록 조회", response_model=DeviceListResponse)
async def get_list(user: ActiveUser, db: DBSession) -> DeviceListResponse:
    return DeviceListResponse(message="기기 목록 조회 성공", data=await devices.get_list(db=db, user=user))


@router.put("/me/push-token", name="푸시 토큰 수정", response_model=DeviceResponse)
async def update_push_token(device: ActiveDevice, body: UpdatePushTokenRequest, db: DBSession) -> DeviceResponse:
    return DeviceResponse(
        message="푸시 토큰 수정 성공", data=await devices.update_push_token(db=db, device=device, data=body)
    )


@router.patch("/me", name="기기 정보 수정", response_model=DeviceResponse)
async def update_me(device: ActiveDevice, body: UpdateDeviceRequest, db: DBSession) -> DeviceResponse:
    return DeviceResponse(message="기기 정보 수정 성공", data=await devices.update_me(db=db, device=device, data=body))


@router.delete("/me", name="기기 해제")
async def delete_me(device: ActiveDevice, db: DBSession) -> BaseResponse:
    await devices.delete_me(db=db, device=device)

    return BaseResponse(message="기기 해제 성공")

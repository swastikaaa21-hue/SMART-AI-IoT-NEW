"""
Device CRUD and status endpoints — Supabase primary.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.db.supabase_session import get_db
from app.middleware.auth import get_current_user
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.device import DeviceCreate, DeviceResponse, DeviceUpdate
from app.services.device_manager import device_manager
from app.utils.exceptions import AlreadyExistsError, NotFoundError

router = APIRouter()


@router.get("", response_model=PaginatedResponse[DeviceResponse])
async def list_devices(
    room_id: str | None = Query(None),
    device_type: str | None = Query(None),
    is_online: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """List devices with optional filters."""
    devices, total = await device_manager.list_devices(
        room_id=room_id, device_type=device_type,
        is_online=is_online, page=page, page_size=page_size,
    )
    return PaginatedResponse.create(
        items=[DeviceResponse(**d) for d in devices],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get a single device by its device_id."""
    device = await device_manager.get_device(device_id)
    if not device:
        raise NotFoundError("Device", device_id)
    return device


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(
    body: DeviceCreate,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Register a new IoT device."""
    existing = await device_manager.get_device(body.device_id)
    if existing:
        raise AlreadyExistsError("Device", body.device_id)

    device = await device_manager.create_device(
        device_id=body.device_id,
        name=body.name,
        device_type=body.device_type,
        room_id=body.room_id,
        state=body.state or "off",
        is_online=True,
        firmware_version=body.firmware_version,
        description=body.description,
        extra_metadata=body.extra_metadata,
    )
    return device


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    body: DeviceUpdate,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update device attributes."""
    update_data = body.model_dump(exclude_unset=True)
    device = await device_manager.update_device(device_id, **update_data)
    if not device:
        raise NotFoundError("Device", device_id)
    return device


@router.delete("/{device_id}", response_model=SuccessResponse)
async def delete_device(
    device_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Remove a device from the system."""
    deleted = await device_manager.delete_device(device_id)
    if not deleted:
        raise NotFoundError("Device", device_id)
    return SuccessResponse(message=f"Device '{device_id}' deleted successfully")

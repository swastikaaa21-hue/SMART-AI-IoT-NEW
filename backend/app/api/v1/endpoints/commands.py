"""
Device command endpoints — Supabase primary.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.db.supabase_session import get_db
from app.middleware.auth import get_current_user
from app.schemas.common import PaginatedResponse
from app.schemas.device import DeviceCommandRequest, DeviceCommandResponse
from app.services.device_manager import device_manager
from app.utils.exceptions import BadRequestError, NotFoundError

router = APIRouter()


@router.post("/{device_id}", response_model=DeviceCommandResponse)
async def send_command(
    device_id: str,
    body: DeviceCommandRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Send a command to a specific device."""
    result = await device_manager.send_command(
        device_id=device_id, 
        action=body.action,
        value=body.value, 
        source="api",
        target_temperature=body.target_temperature,
        ac_mode=body.ac_mode,
        fan_speed=body.fan_speed,
        timer_minutes=body.timer_minutes,
    )
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error")
        if "not found" in error_msg.lower():
            raise NotFoundError("Device", device_id)
        raise BadRequestError(error_msg)

    return DeviceCommandResponse(
        device_id=result["device_id"],
        action=result["action"],
        payload_sent=result["payload_sent"],
        status=result["status"],
        message=result["message"],
    )


@router.get("/logs/{device_id}")
async def get_command_logs(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get command history for a specific device."""
    offset = (page - 1) * page_size
    logs, total = await device_manager.get_command_logs(
        device_id=device_id, limit=page_size, offset=offset,
    )
    return PaginatedResponse.create(
        items=[{
            "id": log.get("id", ""),
            "device_id": log.get("device_id", ""),
            "action": log.get("action", ""),
            "payload": log.get("payload"),
            "source": log.get("source", ""),
            "status": log.get("status", ""),
            "error_message": log.get("error_message"),
            "executed_at": log.get("executed_at", ""),
        } for log in logs],
        total=total, page=page, page_size=page_size,
    )


@router.get("/logs/")
async def get_all_command_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get all command logs across all devices."""
    offset = (page - 1) * page_size
    logs, total = await device_manager.get_command_logs(
        device_id=None, limit=page_size, offset=offset,
    )
    return PaginatedResponse.create(
        items=[{
            "id": log.get("id", ""),
            "device_id": log.get("device_id", ""),
            "action": log.get("action", ""),
            "payload": log.get("payload"),
            "source": log.get("source", ""),
            "status": log.get("status", ""),
            "error_message": log.get("error_message"),
            "executed_at": log.get("executed_at", ""),
        } for log in logs],
        total=total, page=page, page_size=page_size,
    )

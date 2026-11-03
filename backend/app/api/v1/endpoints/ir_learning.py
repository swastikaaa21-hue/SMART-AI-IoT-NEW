"""
IR Learning endpoints for capturing and managing infrared remote codes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app.services.mysql_service import mysql_service
from app.services.mqtt_service import mqtt_service
from app.services.state_persistence import state_persistence
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger("ir_learning")


class IRCaptureRequest(BaseModel):
    device_id: str


class IRCodeSaveRequest(BaseModel):
    device_id: str
    button_name: str
    button_label: Optional[str] = None
    ir_frequency: str
    protocol: Optional[str] = None
    raw_data: Optional[str] = None


class IRCodeResponse(BaseModel):
    id: str
    device_id: str
    button_name: str
    button_label: Optional[str]
    ir_frequency: str
    protocol: Optional[str]
    created_at: str


@router.post("/devices/{device_id}/ir/start-capture")
async def start_ir_capture(
    device_id: str,
    user: dict = Depends(get_current_user),
):
    """Start IR learning mode - tells hardware to listen for IR signal."""
    device = await mysql_service.get_device_by_device_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Send MQTT command to hardware to start IR capture mode
    topic = f"smart-aiot/{device_id}/ir/capture"
    payload = {"action": "start_capture", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    mqtt_service.publish(topic, payload)
    logger.info("ir_capture_started", device_id=device_id)
    
    return {"status": "capturing", "message": "Point remote at sensor and press button"}


@router.get("/devices/{device_id}/ir/codes")
async def list_ir_codes(
    device_id: str,
    user: dict = Depends(get_current_user),
) -> List[IRCodeResponse]:
    """List all learned IR codes for a device."""
    codes = await mysql_service.get_ir_codes_by_device(device_id)
    return [IRCodeResponse(**code) for code in codes]


@router.post("/devices/{device_id}/ir/save", response_model=IRCodeResponse, status_code=201)
async def save_ir_code(
    device_id: str,
    body: IRCodeSaveRequest,
    user: dict = Depends(get_current_user),
):
    """Save captured IR code to database with guaranteed persistence."""
    device = await mysql_service.get_device_by_device_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Use state_persistence service for reliable saving with retry logic
    success, error = await state_persistence.save_ir_code(
        device_id=device_id,
        button_name=body.button_name,
        ir_frequency=body.ir_frequency,
        protocol=body.protocol,
        button_label=body.button_label
    )
    
    if not success:
        logger.error("ir_code_save_failed", device_id=device_id, button=body.button_name, error=error)
        raise HTTPException(status_code=500, detail=f"Failed to save IR code: {error}")
    
    # Retrieve saved code to return
    saved_code = await mysql_service.get_ir_code_by_button(device_id, body.button_name)
    if not saved_code:
        raise HTTPException(status_code=500, detail="IR code saved but could not retrieve")
    
    return IRCodeResponse(**saved_code)


@router.delete("/devices/{device_id}/ir/codes/{button_name}")
async def delete_ir_code(
    device_id: str,
    button_name: str,
    user: dict = Depends(get_current_user),
):
    """Delete a learned IR code."""
    code = await mysql_service.get_ir_code_by_button(device_id, button_name)
    if not code:
        raise HTTPException(status_code=404, detail="IR code not found")
    
    await mysql_service.delete_ir_code(code["id"])
    logger.info("ir_code_deleted", device_id=device_id, button=button_name)
    
    return {"status": "deleted"}

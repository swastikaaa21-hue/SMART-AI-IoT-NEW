"""
Device schemas for CRUD, commands, and status updates.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    device_id: str = Field(..., max_length=100, examples=["esp32_light_01"])
    name: str = Field(..., max_length=150, examples=["Living Room Light"])
    device_type: str = Field(..., max_length=50, examples=["light"])
    room_id: uuid.UUID
    state: str | None = "off"
    firmware_version: str | None = None
    description: str | None = None
    extra_metadata: dict | None = None


class DeviceUpdate(BaseModel):
    name: str | None = None
    device_type: str | None = None
    room_id: uuid.UUID | None = None
    firmware_version: str | None = None
    description: str | None = None
    extra_metadata: dict | None = None


class DeviceResponse(BaseModel):
    id: uuid.UUID
    device_id: str
    name: str
    device_type: str
    room_id: uuid.UUID
    state: str
    brightness: int | None
    temperature: float | None
    humidity: float | None
    target_temperature: int | None
    ac_mode: str | None
    fan_speed: int | None
    timer_minutes: int | None
    extra_metadata: dict | None
    is_online: bool
    firmware_version: str | None
    description: str | None
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeviceCommandRequest(BaseModel):
    """Request to send a command to a device via MQTT."""
    action: str = Field(
        ...,
        examples=["turn_on"],
        description="Command action: turn_on, turn_off, toggle, set_temperature, set_brightness, set_fan_speed, set_timer",
    )
    value: int | float | str | None = Field(
        None,
        description="Optional value for set actions (e.g., brightness level, temperature)",
    )
    target_temperature: int | None = None
    ac_mode: str | None = None
    fan_speed: int | None = None
    timer_minutes: int | None = None


class DeviceCommandResponse(BaseModel):
    device_id: str
    action: str
    payload_sent: dict
    status: str = "sent"
    message: str


class DeviceStatusUpdate(BaseModel):
    """Payload received from ESP32 via MQTT status topic."""
    state: str = Field(..., pattern="^(on|off)$")
    timestamp: int
    brightness: int | None = None
    temperature: float | None = None
    humidity: float | None = None
    extra: dict | None = None

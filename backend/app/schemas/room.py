"""
Room schemas for CRUD operations.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.device import DeviceResponse


class RoomCreate(BaseModel):
    name: str = Field(..., max_length=100, examples=["Living Room"])
    slug: str = Field(..., max_length=100, examples=["living_room"])
    room_type: str = Field(..., max_length=50, examples=["living_room"])
    description: str | None = None
    icon: str | None = Field(None, max_length=50, examples=["mdi:sofa"])


class RoomUpdate(BaseModel):
    name: str | None = None
    room_type: str | None = None
    description: str | None = None
    icon: str | None = None


class RoomResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    room_type: str
    description: str | None
    icon: str | None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    total_devices_count: int = 0
    active_devices_count: int = 0

    class Config:
        from_attributes = True


class RoomWithDevices(RoomResponse):
    devices: list[DeviceResponse] = []

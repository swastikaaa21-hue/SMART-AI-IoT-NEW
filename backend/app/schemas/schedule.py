"""Schedule/Routine schemas."""

from datetime import time
from typing import Optional
from pydantic import BaseModel, Field


class ScheduleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    room_id: str
    device_id: str
    action: str  # turn_on, turn_off, set_temperature, etc
    start_time: str  # HH:MM format
    end_time: Optional[str] = None  # HH:MM format, nullable
    days: str = "1,2,3,4,5,6,7"  # comma-separated days
    parameters: Optional[str] = None  # JSON string for device params


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    action: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    is_active: Optional[bool] = None
    days: Optional[str] = None
    parameters: Optional[str] = None


class ScheduleResponse(ScheduleBase):
    id: str
    is_active: bool
    user_id: str
    room_name: Optional[str] = None
    device_name: Optional[str] = None

    class Config:
        from_attributes = True

"""
Telemetry schemas for sensor data logging and querying.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TelemetryCreate(BaseModel):
    device_id: str
    temperature: float | None = None
    humidity: float | None = None
    power_watts: float | None = None
    extra_data: dict | None = None


class TelemetryResponse(BaseModel):
    id: uuid.UUID
    device_id: str
    temperature: float | None
    humidity: float | None
    power_watts: float | None
    extra_data: dict | None
    recorded_at: datetime

    class Config:
        from_attributes = True


class TelemetryQuery(BaseModel):
    device_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

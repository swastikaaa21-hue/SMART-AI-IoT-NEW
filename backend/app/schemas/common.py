"""
Common response schemas shared across endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
    timestamp: datetime
    services: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
    timestamp: datetime | None = None


class SuccessResponse(BaseModel):
    message: str
    success: bool = True


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[Any],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse":
        total_pages = max(1, (total + page_size - 1) // page_size)
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class MQTTPayload(BaseModel):
    """Standard MQTT message payload between backend and ESP32."""
    state: str = Field(..., pattern="^(on|off)$")
    timestamp: int

    class Config:
        json_schema_extra = {
            "example": {
                "state": "on",
                "timestamp": 1735900000,
            }
        }

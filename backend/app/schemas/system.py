"""
System and configuration schemas for frontend-backend integration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class SystemConfigResponse(BaseModel):
    """Configuration details exposed for the frontend."""
    app_name: str
    app_version: str
    app_env: str
    api_v1_prefix: str
    gemini_api_key: str
    gemini_model: str
    gemini_temperature: float
    gemini_max_tokens: int
    gemini_configured: bool
    mqtt_broker: str
    mqtt_port: int
    mqtt_username: str
    mqtt_tls_enabled: bool
    mqtt_connected: bool
    jwt_access_token_expire_minutes: int


class SystemConfigUpdate(BaseModel):
    """Payload to update runtime configuration."""
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    gemini_temperature: Optional[float] = None
    gemini_max_tokens: Optional[int] = None
    mqtt_broker: Optional[str] = None
    mqtt_port: Optional[int] = None
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None


class SystemStatusResponse(BaseModel):
    """Real-time system diagnostics and telemetry counts."""
    status: str
    version: str
    environment: str
    timestamp: datetime
    mqtt_connected: bool
    gemini_ready: bool
    ws_active_connections: int
    total_rooms: int
    total_devices: int
    online_devices: int
    active_devices: int
    average_temperature: Optional[float] = None
    average_humidity: Optional[float] = None


class SystemTopicItem(BaseModel):
    device_id: str
    name: str
    room_slug: str
    command_topic: str
    status_topic: str
    telemetry_topic: str


class SystemTopicsResponse(BaseModel):
    broker: str
    port: int
    tls: bool
    status_wildcard: str
    telemetry_wildcard: str
    devices: list[SystemTopicItem]


class SeedResponse(BaseModel):
    status: str
    message: str
    rooms_count: int
    devices_count: int

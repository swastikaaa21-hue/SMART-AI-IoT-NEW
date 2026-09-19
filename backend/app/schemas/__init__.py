# app/schemas/__init__.py
"""Pydantic request/response schemas."""

from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    TokenResponse,
    TokenRefreshRequest,
)
from app.schemas.device import (
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
    DeviceCommandRequest,
    DeviceCommandResponse,
    DeviceStatusUpdate,
)
from app.schemas.room import RoomCreate, RoomResponse, RoomUpdate, RoomWithDevices
from app.schemas.telemetry import TelemetryCreate, TelemetryResponse, TelemetryQuery
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    AIChatRequest,
    AIChatResponse,
)
from app.schemas.voice import (
    VoiceTranscribeResponse,
    VoiceSynthesizeRequest,
    VoiceChatResponse,
)
from app.schemas.common import (
    HealthResponse,
    PaginatedResponse,
    ErrorResponse,
    SuccessResponse,
)

__all__ = [
    "UserCreate", "UserLogin", "UserResponse", "UserUpdate",
    "TokenResponse", "TokenRefreshRequest",
    "DeviceCreate", "DeviceResponse", "DeviceUpdate",
    "DeviceCommandRequest", "DeviceCommandResponse", "DeviceStatusUpdate",
    "RoomCreate", "RoomResponse", "RoomUpdate", "RoomWithDevices",
    "TelemetryCreate", "TelemetryResponse", "TelemetryQuery",
    "ChatMessageCreate", "ChatMessageResponse",
    "ChatSessionCreate", "ChatSessionResponse",
    "AIChatRequest", "AIChatResponse",
    "HealthResponse", "PaginatedResponse", "ErrorResponse", "SuccessResponse",
]

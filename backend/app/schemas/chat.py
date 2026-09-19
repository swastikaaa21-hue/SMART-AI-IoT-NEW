"""
Chat and AI interaction schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=255)


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    role: str = Field(default="user", pattern="^(user|assistant|system|function)$")


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    function_call: str | None
    function_response: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AIChatRequest(BaseModel):
    """Request from frontend to the AI chat endpoint."""
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: uuid.UUID | None = None
    room_context: str | None = None


class AIChatResponse(BaseModel):
    """Response from AI chat endpoint."""
    reply: str = Field(..., examples=["Baik, lampu utama di ruang tamu telah dinyalakan!"])
    session_id: str
    function_called: str | None = Field(None, examples=["control_device"])
    function_result: dict | None = Field(None, examples=[{"success": True, "device_id": "esp32_light_01"}])
    devices_affected: list[str] = Field(default_factory=list, examples=[["esp32_light_01"]])

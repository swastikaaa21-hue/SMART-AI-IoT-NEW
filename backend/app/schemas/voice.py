"""
Voice interaction schemas for STT, TTS, and Voice AI Chat.
"""

from __future__ import annotations

import uuid
from pydantic import BaseModel, Field


class VoiceTranscribeResponse(BaseModel):
    """Result of speech-to-text transcription."""
    transcript: str = Field(..., description="Recognized text from audio")
    language: str = Field(default="id-ID", description="Language code")
    success: bool = Field(default=True, description="Whether speech was successfully recognized")


class VoiceSynthesizeRequest(BaseModel):
    """Request to synthesize text to audio speech."""
    text: str = Field(..., min_length=1, max_length=2000, description="Indonesian text to synthesize")
    language: str = Field(default="id", description="Language code (default: id)")
    slow: bool = Field(default=False, description="Whether to speak slowly")


class VoiceChatResponse(BaseModel):
    """Full response for voice AI command."""
    transcript: str = Field(..., description="User's transcribed voice command in Indonesian")
    reply: str = Field(..., description="AI assistant's response text")
    audio_base64: str = Field(..., description="Base64 encoded MP3 audio response")
    session_id: uuid.UUID = Field(..., description="Chat session ID")
    function_called: str | None = Field(None, description="IoT function executed if any")
    function_result: dict | None = Field(None, description="Result of IoT function")
    devices_affected: list[str] = Field(default_factory=list, description="IDs of affected IoT devices")

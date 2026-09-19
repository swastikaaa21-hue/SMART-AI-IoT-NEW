"""
Voice endpoints for Indonesian Speech-to-Text, Text-to-Speech, and Voice AI Chat.
Supabase primary.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from app.api.v1.endpoints.chat import _execute_function
from app.db.supabase_session import get_db
from app.middleware.auth import get_current_user
from app.schemas.voice import (
    VoiceChatResponse,
    VoiceSynthesizeRequest,
    VoiceTranscribeResponse,
)
from app.services.gemini_service import gemini_service
from app.services.supabase_service import supabase_service
from app.services.voice_service import voice_service
from app.utils.exceptions import NotFoundError

router = APIRouter()


def _gen_id() -> str:
    return str(uuid.uuid4()).replace("-", "")


@router.post("/transcribe", response_model=VoiceTranscribeResponse, summary="Transcribe audio to Indonesian text")
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (WAV, MP3, OGG, WebM)"),
    user: dict = Depends(get_current_user),
) -> VoiceTranscribeResponse:
    """Transcribe uploaded Indonesian voice audio into text."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded audio file is empty")

    transcript = voice_service.transcribe_audio_bytes(audio_bytes, language="id-ID")
    return VoiceTranscribeResponse(transcript=transcript, language="id-ID", success=bool(transcript.strip()))


@router.post("/synthesize", summary="Convert Indonesian text to speech audio", response_class=Response)
async def synthesize_speech(
    body: VoiceSynthesizeRequest,
    user: dict = Depends(get_current_user),
) -> Response:
    """Convert text to natural-sounding Indonesian speech audio (MP3)."""
    audio_bytes = voice_service.synthesize_speech(text=body.text, language=body.language, slow=body.slow)
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate speech audio")
    return Response(content=audio_bytes, media_type="audio/mpeg",
                    headers={"Content-Disposition": 'inline; filename="speech.mp3"'})


@router.post("/chat", response_model=VoiceChatResponse, summary="Full Voice AI Chat with IoT execution")
async def voice_chat(
    file: UploadFile = File(..., description="Audio recording of voice command"),
    session_id: str | None = Form(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> VoiceChatResponse:
    """End-to-end voice control: transcribe -> AI -> execute -> synthesize."""
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio file received")

    user_id = str(user["id"])
    now = datetime.now(timezone.utc).isoformat()

    # 1. Speech to Text
    transcript = voice_service.transcribe_audio_bytes(audio_bytes, language="id-ID")

    if not transcript or not transcript.strip():
        fallback_reply = "Maaf, suara tidak terdengar jelas. Boleh tolong diulang kembali?"
        fallback_audio = voice_service.synthesize_speech(fallback_reply)
        return VoiceChatResponse(
            transcript="", reply=fallback_reply,
            audio_base64=voice_service.bytes_to_base64(fallback_audio) if fallback_audio else "",
            session_id=session_id or _gen_id(),
            function_called=None, function_result=None, devices_affected=[],
        )

    # 2. Get or create chat session
    if session_id:
        session = await supabase_service.get_chat_session(session_id, user_id)
        if not session:
            raise NotFoundError("ChatSession", session_id)
        sid = session["id"]
    else:
        sid = _gen_id()
        session = await supabase_service.create_chat_session({
            "id": sid, "user_id": user_id,
            "title": f"🎙️ {transcript[:45]}" + ("..." if len(transcript) > 45 else ""),
            "is_active": True, "created_at": now, "updated_at": now,
        })

    # 3. Save user message
    await supabase_service.create_chat_message({
        "id": _gen_id(), "session_id": sid, "role": "user", "content": transcript, "created_at": now,
    })

    # 4. Execute AI + Function Calling
    async def executor(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return await _execute_function(name, args)

    ai_result = await gemini_service.chat(message=transcript, session_id=sid, function_executor=executor)
    reply_text = ai_result.get("reply", "")

    # 5. Save assistant message
    await supabase_service.create_chat_message({
        "id": _gen_id(), "session_id": sid, "role": "assistant", "content": reply_text,
        "function_call": ai_result.get("function_called"),
        "function_response": json.dumps(ai_result.get("function_result")) if ai_result.get("function_result") else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # 6. Synthesize reply
    reply_audio_bytes = voice_service.synthesize_speech(reply_text)
    audio_base64 = voice_service.bytes_to_base64(reply_audio_bytes) if reply_audio_bytes else ""

    return VoiceChatResponse(
        transcript=transcript, reply=reply_text, audio_base64=audio_base64,
        session_id=sid,
        function_called=ai_result.get("function_called"),
        function_result=ai_result.get("function_result"),
        devices_affected=ai_result.get("devices_affected", []),
    )

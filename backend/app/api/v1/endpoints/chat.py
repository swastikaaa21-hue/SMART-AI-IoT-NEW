"""
AI Chat endpoints with Gemini Function Calling — Supabase primary.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.logging import get_logger
from app.db.supabase_session import get_db
from app.middleware.auth import get_current_user
from app.schemas.chat import (
    AIChatRequest,
    AIChatResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageResponse,
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.services.device_manager import device_manager
from app.services.gemini_service import gemini_service
from app.services.supabase_service import supabase_service
from app.utils.exceptions import NotFoundError

logger = get_logger("chat")

router = APIRouter()


def _normalize_room_slug(slug_or_name: str | None) -> str:
    if not slug_or_name:
        return ""
    clean = slug_or_name.lower().strip().replace(" ", "-").replace("_", "-")
    aliases = {
        "bedroom": "kamar", "kamar-tidur": "kamar",
        "living-room": "ruang-tamu", "livingroom": "ruang-tamu", "ruang-keluarga": "ruang-tamu",
        "meeting-room": "ruang-rapat", "office": "ruang-rapat", "ruang-kerja": "ruang-rapat",
    }
    return aliases.get(clean, clean)


async def _execute_function(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute an IoT function requested by Gemini."""

    if name == "control_device":
        dev_id = args.get("device_id", "")
        action = args.get("action", "")
        if action in ["nyalakan", "hidupkan", "on"]:
            action = "turn_on"
        elif action in ["matikan", "padamkan", "off"]:
            action = "turn_off"
        return await device_manager.send_command(
            device_id=dev_id, action=action, value=args.get("value"), source="ai",
        )

    elif name == "get_device_status":
        device = await device_manager.get_device(args.get("device_id", ""))
        if not device:
            return {"error": f"Device '{args.get('device_id')}' not found"}
        return {
            "device_id": device.get("device_id"),
            "name": device.get("name"),
            "state": device.get("state"),
            "is_online": device.get("is_online"),
            "device_type": device.get("device_type"),
            "temperature": device.get("temperature"),
            "humidity": device.get("humidity"),
            "brightness": device.get("brightness"),
            "last_seen_at": device.get("last_seen_at"),
        }

    elif name == "list_devices":
        raw_room = args.get("room")
        room_slug = _normalize_room_slug(raw_room) if raw_room else None
        dtype = args.get("device_type")

        room_id = None
        if room_slug:
            # Find room by slug across all owners
            all_rooms = await supabase_service.client.table("rooms").select("*").eq("slug", room_slug).execute()
            if all_rooms.data:
                room_id = all_rooms.data[0]["id"]

        devices, total = await device_manager.list_devices(room_id=room_id, device_type=dtype, page=1, page_size=50)
        return {
            "total": total,
            "devices": [{
                "device_id": d.get("device_id"), "name": d.get("name"),
                "type": d.get("device_type"), "state": d.get("state"),
                "is_online": d.get("is_online"),
                "room_name": d.get("room", {}).get("name"),
                "room_slug": d.get("room", {}).get("slug"),
            } for d in devices],
        }

    elif name == "get_telemetry":
        limit = min(args.get("limit", 10), 100)
        logs, total = await device_manager.get_telemetry(device_id=args.get("device_id"), limit=limit)
        return {
            "device_id": args.get("device_id"),
            "total_records": total,
            "readings": [{
                "temperature": log.get("temperature"),
                "humidity": log.get("humidity"),
                "power_watts": log.get("power_watts"),
                "recorded_at": log.get("recorded_at", ""),
            } for log in logs],
        }

    elif name == "control_room_devices":
        raw_room = args.get("room", "")
        room_slug = _normalize_room_slug(raw_room)
        action = args.get("action", "")
        if action in ["nyalakan", "hidupkan", "on"]:
            action = "turn_on"
        elif action in ["matikan", "padamkan", "off"]:
            action = "turn_off"
        dtype = args.get("device_type")

        # Resolve room
        room = None
        # Try slug
        if room_slug:
            resp = supabase_service.client.table("rooms").select("*").eq("slug", room_slug).execute()
            if resp.data:
                room = resp.data[0]
        # Try name (case-insensitive)
        if not room:
            resp = supabase_service.client.table("rooms").select("*").ilike("name", str(raw_room).strip()).execute()
            if resp.data:
                room = resp.data[0]
        if not room:
            return {"success": False, "error": f"Room '{raw_room}' not found"}

        # Get devices in room
        devices = await supabase_service.get_devices_by_room(room["id"])
        if dtype:
            devices = [d for d in devices if d.get("device_type") == dtype]
        if not devices:
            return {"success": False, "error": f"No devices found in room '{room.get('name')}'"}

        results = []
        affected = []
        for d in devices:
            cmd = await device_manager.send_command(device_id=d["device_id"], action=action, source="ai")
            results.append(cmd)
            affected.append(d["device_id"])

        ok = sum(1 for r in results if r.get("success"))
        return {
            "success": ok > 0,
            "room": room.get("name"),
            "action": action,
            "total_devices": len(devices),
            "success_count": ok,
            "devices": affected,
        }

    return {"error": f"Unknown function: {name}"}


def _gen_id() -> str:
    return str(uuid.uuid4()).replace("-", "")


@router.post("/message", response_model=AIChatResponse)
async def send_chat_message(
    body: AIChatRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Send a natural language message to the AI assistant."""
    user_id = str(user["id"])
    now = datetime.now(timezone.utc).isoformat()

    # Get or create chat session (fallback seamlessly if session_id is stale/invalid)
    session = None
    if body.session_id:
        session = await supabase_service.get_chat_session(str(body.session_id), user_id)

    if not session:
        session_id = _gen_id()
        session = await supabase_service.create_chat_session({
            "id": session_id,
            "user_id": user_id,
            "title": body.message[:50] + ("..." if len(body.message) > 50 else ""),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })

    sid = session["id"]

    # Save user message
    await supabase_service.create_chat_message({
        "id": _gen_id(),
        "session_id": sid,
        "role": "user",
        "content": body.message,
        "created_at": now,
    })

    # Function executor
    async def executor(name: str, args: dict) -> dict:
        return await _execute_function(name, args)

    # Contextual prompt
    prompt = (
        f"[Konteks Ruangan: User sedang membuka ruangan '{body.room_context}']\n{body.message}"
        if body.room_context else body.message
    )

    # Process through Gemini
    ai_result = await gemini_service.chat(
        message=prompt, session_id=sid, function_executor=executor,
    )

    # Save assistant message
    await supabase_service.create_chat_message({
        "id": _gen_id(),
        "session_id": sid,
        "role": "assistant",
        "content": ai_result["reply"],
        "function_call": ai_result.get("function_called"),
        "function_response": json.dumps(ai_result.get("function_result")) if ai_result.get("function_result") else None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return AIChatResponse(
        reply=ai_result["reply"],
        session_id=sid,
        function_called=ai_result.get("function_called"),
        function_result=ai_result.get("function_result"),
        devices_affected=ai_result.get("devices_affected", []),
    )


# ── Chat Session CRUD ───────────────────────────────────────

@router.get("/sessions", response_model=PaginatedResponse[ChatSessionResponse])
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """List all chat sessions for the current user."""
    offset = (page - 1) * page_size
    sessions, total = await supabase_service.get_chat_sessions(
        str(user["id"]), limit=page_size, offset=offset,
    )
    return PaginatedResponse.create(
        items=[ChatSessionResponse(**s) for s in sessions],
        total=total, page=page, page_size=page_size,
    )


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    body: ChatSessionCreate,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Create a new chat session."""
    now = datetime.now(timezone.utc).isoformat()
    session = await supabase_service.create_chat_session({
        "id": _gen_id(),
        "user_id": str(user["id"]),
        "title": body.title,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })
    return session


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_session_messages(
    session_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get all messages in a chat session."""
    session = await supabase_service.get_chat_session(session_id, str(user["id"]))
    if not session:
        raise NotFoundError("ChatSession", session_id)
    messages = await supabase_service.get_chat_messages(session_id)
    return [ChatMessageResponse(**m) for m in messages]


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete a chat session and all its messages."""
    session = await supabase_service.get_chat_session(session_id, str(user["id"]))
    if not session:
        raise NotFoundError("ChatSession", session_id)

    gemini_service.clear_session(session_id)
    await supabase_service.delete_chat_session(session_id)
    return SuccessResponse(message="Chat session deleted successfully")

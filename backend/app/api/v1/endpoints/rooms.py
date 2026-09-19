"""
Room management endpoints — Supabase primary.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.db.supabase_session import get_db
from app.middleware.auth import get_current_user
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.schemas.room import RoomCreate, RoomResponse, RoomUpdate, RoomWithDevices
from app.utils.exceptions import AlreadyExistsError, NotFoundError
from app.services.supabase_service import supabase_service
from app.services.seed_service import seed_user_default_data

router = APIRouter()


@router.get("", response_model=PaginatedResponse[RoomResponse])
async def list_rooms(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """List all rooms belonging to the current user."""
    owner_id = str(user["id"])
    rooms = await supabase_service.get_rooms_by_owner_with_devices(owner_id)

    # Auto-seed if empty
    if not rooms:
        await seed_user_default_data(owner_id, reset=False)
        rooms = await supabase_service.get_rooms_by_owner_with_devices(owner_id)

    total = len(rooms)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = rooms[start:end]

    items = []
    for r in page_items:
        resp = RoomResponse(
            id=r["id"],
            name=r["name"],
            slug=r["slug"],
            room_type=r["room_type"],
            description=r.get("description"),
            icon=r.get("icon"),
            owner_id=r["owner_id"],
            created_at=r.get("created_at"),
            updated_at=r.get("updated_at"),
            total_devices_count=r.get("total_devices_count", 0),
            active_devices_count=r.get("active_devices_count", 0),
        )
        items.append(resp)

    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get("/{room_id}", response_model=RoomWithDevices)
async def get_room(
    room_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get a single room with its devices."""
    room = await supabase_service.get_room_by_id(room_id)
    if not room or room.get("owner_id") != str(user["id"]):
        raise NotFoundError("Room", room_id)

    devices = await supabase_service.get_devices_by_room(room_id)
    room["devices"] = devices
    room["total_devices_count"] = len(devices)
    room["active_devices_count"] = sum(1 for d in devices if d.get("state") == "on")
    return room


@router.post("", response_model=RoomResponse, status_code=201)
async def create_room(
    body: RoomCreate,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Create a new room."""
    owner_id = str(user["id"])
    existing = await supabase_service.get_room_by_slug(body.slug, owner_id)
    if existing:
        raise AlreadyExistsError("Room", body.slug)

    now = datetime.now(timezone.utc).isoformat()
    room_id = str(uuid.uuid4()).replace("-", "")
    room = await supabase_service.create_room({
        "id": room_id,
        "name": body.name,
        "slug": body.slug,
        "room_type": body.room_type,
        "description": body.description,
        "icon": body.icon,
        "owner_id": owner_id,
        "created_at": now,
        "updated_at": now,
    })
    room["total_devices_count"] = 0
    room["active_devices_count"] = 0
    return room


@router.patch("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: str,
    body: RoomUpdate,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update an existing room."""
    room = await supabase_service.get_room_by_id(room_id)
    if not room or room.get("owner_id") != str(user["id"]):
        raise NotFoundError("Room", room_id)

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.room_type is not None:
        updates["room_type"] = body.room_type
    if body.description is not None:
        updates["description"] = body.description
    if body.icon is not None:
        updates["icon"] = body.icon

    if updates:
        room = await supabase_service.update_room(room_id, updates)

    devices = await supabase_service.get_devices_by_room(room_id)
    room["total_devices_count"] = len(devices)
    room["active_devices_count"] = sum(1 for d in devices if d.get("state") == "on")
    return room


@router.delete("/{room_id}", response_model=SuccessResponse)
async def delete_room(
    room_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete a room and all its associated devices."""
    room = await supabase_service.get_room_by_id(room_id)
    if not room or room.get("owner_id") != str(user["id"]):
        raise NotFoundError("Room", room_id)

    await supabase_service.delete_room(room_id)
    return SuccessResponse(message=f"Room '{room.get('name', room_id)}' deleted successfully")

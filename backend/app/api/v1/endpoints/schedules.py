"""Schedule/Routine endpoints — Supabase primary."""

from __future__ import annotations

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.db.supabase_session import get_db
from app.middleware.auth import get_current_user
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.services.supabase_service import supabase_service
from app.utils.exceptions import NotFoundError

router = APIRouter()


def _get_user_id(user: dict | object) -> str:
    if isinstance(user, dict):
        return str(user.get("id", ""))
    return str(getattr(user, "id", ""))


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_in: ScheduleCreate,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Create new schedule/routine."""
    user_id = _get_user_id(user)

    # Verify room and device exist
    room = await supabase_service.get_room_by_id(schedule_in.room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    device = await supabase_service.get_device_by_device_id(schedule_in.device_id)
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    schedule_id = str(uuid.uuid4()).replace("-", "")
    schedule_data = {
        "id": schedule_id,
        "name": schedule_in.name,
        "room_id": str(schedule_in.room_id),
        "device_id": schedule_in.device_id,
        "action": schedule_in.action,
        "start_time": schedule_in.start_time,
        "end_time": schedule_in.end_time,
        "is_active": True,
        "days": schedule_in.days,
        "parameters": schedule_in.parameters,
        "user_id": user_id,
    }

    created = await supabase_service.create_schedule(schedule_data)
    if not created:
        created = schedule_data

    return ScheduleResponse(
        id=created.get("id", schedule_id),
        name=created.get("name", schedule_in.name),
        room_id=created.get("room_id", schedule_in.room_id),
        device_id=created.get("device_id", schedule_in.device_id),
        action=created.get("action", schedule_in.action),
        start_time=created.get("start_time", schedule_in.start_time),
        end_time=created.get("end_time", schedule_in.end_time),
        is_active=created.get("is_active", True),
        days=created.get("days", schedule_in.days),
        parameters=created.get("parameters", schedule_in.parameters),
        user_id=user_id,
        room_name=room.get("name"),
        device_name=device.get("name"),
    )


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """List all schedules for current user."""
    user_id = _get_user_id(user)
    schedules = await supabase_service.get_user_schedules(user_id)

    rooms_cache: dict[str, dict] = {}
    devices_cache: dict[str, dict] = {}
    responses: list[ScheduleResponse] = []

    for s in schedules:
        rid = s.get("room_id", "")
        did = s.get("device_id", "")

        if rid and rid not in rooms_cache:
            rooms_cache[rid] = await supabase_service.get_room_by_id(rid) or {}
        if did and did not in devices_cache:
            devices_cache[did] = await supabase_service.get_device_by_device_id(did) or {}

        room = rooms_cache.get(rid, {})
        device = devices_cache.get(did, {})

        responses.append(ScheduleResponse(
            id=s.get("id", ""),
            name=s.get("name", ""),
            room_id=rid,
            device_id=did,
            action=s.get("action", ""),
            start_time=s.get("start_time", ""),
            end_time=s.get("end_time"),
            is_active=s.get("is_active", True),
            days=s.get("days", "1,2,3,4,5,6,7"),
            parameters=s.get("parameters"),
            user_id=user_id,
            room_name=room.get("name"),
            device_name=device.get("name"),
        ))

    return responses


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get schedule detail."""
    user_id = _get_user_id(user)
    schedule = await supabase_service.get_schedule_by_id(schedule_id)
    if not schedule or str(schedule.get("user_id")) != user_id:
        raise NotFoundError("Schedule", schedule_id)

    room = await supabase_service.get_room_by_id(schedule.get("room_id", "")) or {}
    device = await supabase_service.get_device_by_device_id(schedule.get("device_id", "")) or {}

    return ScheduleResponse(
        id=schedule.get("id", schedule_id),
        name=schedule.get("name", ""),
        room_id=schedule.get("room_id", ""),
        device_id=schedule.get("device_id", ""),
        action=schedule.get("action", ""),
        start_time=schedule.get("start_time", ""),
        end_time=schedule.get("end_time"),
        is_active=schedule.get("is_active", True),
        days=schedule.get("days", "1,2,3,4,5,6,7"),
        parameters=schedule.get("parameters"),
        user_id=user_id,
        room_name=room.get("name"),
        device_name=device.get("name"),
    )


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    schedule_in: ScheduleUpdate,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Update schedule."""
    user_id = _get_user_id(user)
    existing = await supabase_service.get_schedule_by_id(schedule_id)
    if not existing or str(existing.get("user_id")) != user_id:
        raise NotFoundError("Schedule", schedule_id)

    updates = schedule_in.model_dump(exclude_unset=True)
    updated = await supabase_service.update_schedule(schedule_id, updates)
    merged = {**existing, **updated, **updates}

    room = await supabase_service.get_room_by_id(merged.get("room_id", "")) or {}
    device = await supabase_service.get_device_by_device_id(merged.get("device_id", "")) or {}

    return ScheduleResponse(
        id=merged.get("id", schedule_id),
        name=merged.get("name", ""),
        room_id=merged.get("room_id", ""),
        device_id=merged.get("device_id", ""),
        action=merged.get("action", ""),
        start_time=merged.get("start_time", ""),
        end_time=merged.get("end_time"),
        is_active=merged.get("is_active", True),
        days=merged.get("days", "1,2,3,4,5,6,7"),
        parameters=merged.get("parameters"),
        user_id=user_id,
        room_name=room.get("name"),
        device_name=device.get("name"),
    )


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Delete schedule."""
    user_id = _get_user_id(user)
    existing = await supabase_service.get_schedule_by_id(schedule_id)
    if not existing or str(existing.get("user_id")) != user_id:
        raise NotFoundError("Schedule", schedule_id)

    await supabase_service.delete_schedule(schedule_id)

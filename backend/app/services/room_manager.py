"""
Room manager service.

Ownership-scoped room resolution and CRUD. Both the REST endpoints and the AI
function-calling layer go through here so slug generation, cascade semantics and
real-time broadcasts stay identical whichever path made the change.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import WSEventType
from app.core.logging import get_logger
from app.models.device import Device
from app.models.room import Room
from app.services.seed_service import unique_room_slug
from app.services.websocket_manager import enqueue_ws_event
from app.utils.helpers import slugify

logger = get_logger("room_manager")

# Casual Indonesian/English names users and the AI say out loud, mapped to the
# slug the seeded rooms actually use.
_ROOM_ALIASES = {
    "bedroom": "kamar",
    "kamar-tidur": "kamar",
    "living-room": "ruang-tamu",
    "livingroom": "ruang-tamu",
    "ruang-keluarga": "ruang-tamu",
    "meeting-room": "ruang-rapat",
    "office": "ruang-rapat",
    "ruang-kerja": "ruang-rapat",
}


def normalize_room_slug(slug_or_name: str | None) -> str:
    """Best-effort conversion of a spoken room reference into a known slug."""
    if not slug_or_name:
        return ""
    clean = slug_or_name.lower().strip().replace(" ", "-").replace("_", "-")
    return _ROOM_ALIASES.get(clean, clean)


class RoomManager:
    """Handles room resolution and structure changes for a single owner."""

    async def resolve_room(
        self,
        db: AsyncSession,
        ref: str | uuid.UUID | None,
        owner_id: uuid.UUID,
    ) -> Room | None:
        """Resolve a room from a UUID, slug, name or fuzzy fragment.

        Every tier is filtered by ``owner_id``: a room belonging to another user
        must never resolve, no matter how good the match is.
        """
        if ref is None:
            return None
        raw = str(ref).strip()
        if not raw:
            return None

        # 1. UUID primary key
        try:
            room_uuid = uuid.UUID(raw)
        except (ValueError, TypeError, AttributeError):
            room_uuid = None
        if room_uuid is not None:
            room = (
                await db.execute(
                    select(Room).where(Room.id == room_uuid, Room.owner_id == owner_id)
                )
            ).scalar_one_or_none()
            if room:
                return room

        # 2. Slug, with spoken aliases normalised first
        slug = normalize_room_slug(raw)
        if slug:
            room = (
                await db.execute(
                    select(Room).where(Room.slug == slug, Room.owner_id == owner_id)
                )
            ).scalar_one_or_none()
            if room:
                return room

        # 3. Exact room name, case-insensitive
        room = (
            await db.execute(
                select(Room).where(
                    func.lower(Room.name) == raw.lower(), Room.owner_id == owner_id
                )
            )
        ).scalar_one_or_none()
        if room:
            return room

        # 4. Fuzzy substring match. Projected to plain columns so a near-miss
        #    does not drag every room's device tree into memory.
        candidates = (
            await db.execute(
                select(Room.id, Room.name, Room.slug).where(Room.owner_id == owner_id)
            )
        ).all()
        clean = raw.lower().replace("-", " ").replace("_", " ").strip()
        for room_id, name, room_slug in candidates:
            slug_spaced = room_slug.lower().replace("-", " ").replace("_", " ")
            if clean in name.lower() or clean in room_slug.lower() or slug_spaced in clean:
                return (
                    await db.execute(select(Room).where(Room.id == room_id))
                ).scalar_one_or_none()

        return None

    async def list_rooms_for_user(self, db: AsyncSession, owner_id: uuid.UUID) -> list[Room]:
        """All rooms owned by a user, oldest first."""
        result = await db.execute(
            select(Room).where(Room.owner_id == owner_id).order_by(Room.created_at)
        )
        return list(result.scalars().all())

    async def create_room(
        self,
        db: AsyncSession,
        owner_id: uuid.UUID,
        name: str,
        room_type: str,
        slug: str | None = None,
        icon: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a room, disambiguating the slug if another user already holds it."""
        base = (slug or slugify(name)).strip("-_")
        if not base:
            return {"success": False, "error": f"Cannot derive a room slug from '{name}'"}

        room = await self._insert_room(db, owner_id, base, name, room_type, icon, description)
        await db.refresh(room)

        logger.info("room_created", room_id=str(room.id), slug=room.slug, owner_id=str(owner_id))
        enqueue_ws_event(
            db,
            WSEventType.STRUCTURE_UPDATE,
            self._event(room, "room_created", owner_id=owner_id, device_ids=[]),
        )
        return {
            "success": True,
            "op": "room_created",
            "id": str(room.id),
            "room_id": str(room.id),
            "name": room.name,
            "slug": room.slug,
            "room_type": room.room_type,
            "icon": room.icon,
            "description": room.description,
            "owner_id": str(owner_id),
            "created_at": room.created_at.isoformat(),
            "updated_at": room.updated_at.isoformat(),
            "total_devices_count": 0,
            "active_devices_count": 0,
            "changes": [{"op": "room_created", "room_id": str(room.id), "name": room.name, "slug": room.slug}],
        }

    async def update_room(
        self,
        db: AsyncSession,
        room: Room,
        *,
        name: str | None = None,
        room_type: str | None = None,
        description: str | None = None,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Update a room's editable fields.

        ``slug`` is deliberately not one of them: it is part of the MQTT topic
        (``home/{slug}/{device_id}/set``), so renaming it would silently
        unsubscribe every ESP32 in that room.
        """
        previous_name = room.name
        if name is not None:
            room.name = name
        if room_type is not None:
            room.room_type = room_type
        if description is not None:
            room.description = description
        if icon is not None:
            room.icon = icon
        await db.flush()

        renamed = room.name != previous_name
        op = "room_renamed" if renamed else "room_updated"

        logger.info(op, room_id=str(room.id), slug=room.slug)
        enqueue_ws_event(
            db,
            WSEventType.STRUCTURE_UPDATE,
            self._event(room, op, previous_name=previous_name),
        )
        return {
            "success": True,
            "op": op,
            "room_id": str(room.id),
            "name": room.name,
            "previous_name": previous_name,
            "slug": room.slug,
            "room_type": room.room_type,
            "icon": room.icon,
            "description": room.description,
            "changes": [
                {
                    "op": op,
                    "room_id": str(room.id),
                    "old_name": previous_name,
                    "new_name": room.name,
                }
            ],
        }

    async def delete_room(self, db: AsyncSession, room: Room) -> dict[str, Any]:
        """Delete a room and cascade to its devices."""
        # Captured before the delete: the ORM objects are expired once flushed.
        device_ids = list(
            (
                await db.execute(select(Device.device_id).where(Device.room_id == room.id))
            ).scalars().all()
        )
        room_id, name, slug, owner_id = room.id, room.name, room.slug, room.owner_id

        await db.delete(room)
        await db.flush()

        logger.info("room_deleted", room_id=str(room_id), slug=slug, devices=len(device_ids))
        enqueue_ws_event(
            db,
            WSEventType.STRUCTURE_UPDATE,
            {
                "op": "room_deleted",
                "owner_id": str(owner_id),
                "room_id": str(room_id),
                "name": name,
                "slug": slug,
                "device_ids": device_ids,
            },
        )
        return {
            "success": True,
            "op": "room_deleted",
            "room_id": str(room_id),
            "name": name,
            "slug": slug,
            "device_ids": device_ids,
            "devices_deleted": len(device_ids),
            "changes": [
                {
                    "op": "room_deleted",
                    "room_id": str(room_id),
                    "name": name,
                    "device_ids": device_ids,
                }
            ],
        }

    async def _insert_room(
        self,
        db: AsyncSession,
        owner_id: uuid.UUID,
        base_slug: str,
        name: str,
        room_type: str,
        icon: str | None,
        description: str | None,
    ) -> Room:
        """Insert inside a savepoint so a slug race can be retried."""
        slug = await unique_room_slug(db, base_slug, owner_id)
        try:
            async with db.begin_nested():
                room = Room(
                    name=name,
                    slug=slug,
                    room_type=room_type,
                    icon=icon,
                    description=description,
                    owner_id=owner_id,
                )
                db.add(room)
            return room
        except IntegrityError:
            # rooms.slug is globally unique, so a concurrent insert can still win.
            slug = await unique_room_slug(db, f"{base_slug}-{uuid.uuid4().hex[:4]}", owner_id)
            async with db.begin_nested():
                room = Room(
                    name=name,
                    slug=slug,
                    room_type=room_type,
                    icon=icon,
                    description=description,
                    owner_id=owner_id,
                )
                db.add(room)
            return room

    def _event(self, room: Room, op: str, owner_id: uuid.UUID | None = None, **extra: Any) -> dict[str, Any]:
        """Build a STRUCTURE_UPDATE payload; ``owner_id`` routes it, then is stripped."""
        payload: dict[str, Any] = {
            "op": op,
            "owner_id": str(owner_id or room.owner_id),
            "room_id": str(room.id),
            "name": room.name,
            "slug": room.slug,
        }
        payload.update(extra)
        return payload


# Module-level singleton
room_manager = RoomManager()

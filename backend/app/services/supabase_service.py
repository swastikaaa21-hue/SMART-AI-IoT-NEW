"""
MySQL Service — Primary Database Operations via SQLAlchemy async.

Drop-in replacement for the old Supabase service. Same interface,
backed by MySQL (XAMPP) through async SQLAlchemy.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger("mysql_service")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row) -> dict:
    """Convert SQLAlchemy model instance to dict."""
    if row is None:
        return {}
    if isinstance(row, dict):
        return row
    d = {}
    for c in row.__table__.columns:
        val = getattr(row, c.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        d[c.name] = val
    return d


class MySQLService:
    """Singleton service wrapping SQLAlchemy async for MySQL."""

    def __init__(self):
        self._initialized = True

    def initialize(self) -> None:
        self._initialized = True
        logger.info("mysql_service_initialized")

    async def _session(self) -> AsyncSession:
        return AsyncSessionLocal()

    # ── Users ────────────────────────────────────────────────

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.user import User
        async with AsyncSessionLocal() as db:
            user = User(**{k: v for k, v in user_data.items() if hasattr(User, k)})
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("user_created", user_id=user_data.get("id"))
            return _row_to_dict(user)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        from app.models.user import User
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                return _row_to_dict(user) if user else None
        except Exception as e:
            logger.error("user_get_failed", error=str(e), email=email)
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        from app.models.user import User
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                return _row_to_dict(user) if user else None
        except Exception as e:
            logger.error("user_get_failed", error=str(e), user_id=user_id)
            return None

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.user import User
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return {}
            for k, v in updates.items():
                if hasattr(user, k):
                    setattr(user, k, v)
            await db.commit()
            await db.refresh(user)
            return _row_to_dict(user)

    # ── Rooms ────────────────────────────────────────────────

    async def create_room(self, room_data: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.room import Room
        async with AsyncSessionLocal() as db:
            room = Room(**{k: v for k, v in room_data.items() if hasattr(Room, k)})
            db.add(room)
            await db.commit()
            await db.refresh(room)
            logger.info("room_created", room_id=room_data.get("id"))
            return _row_to_dict(room)

    async def get_room_by_id(self, room_id: str) -> Optional[Dict[str, Any]]:
        from app.models.room import Room
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Room).where(Room.id == room_id))
                room = result.scalar_one_or_none()
                return _row_to_dict(room) if room else None
        except Exception as e:
            logger.error("room_get_failed", error=str(e), room_id=room_id)
            return None

    async def get_room_by_slug(self, slug: str, owner_id: str) -> Optional[Dict[str, Any]]:
        from app.models.room import Room
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Room).where(and_(Room.slug == slug, Room.owner_id == owner_id))
                )
                room = result.scalar_one_or_none()
                return _row_to_dict(room) if room else None
        except Exception as e:
            logger.error("room_get_failed", error=str(e), slug=slug)
            return None

    async def get_rooms_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        from app.models.room import Room
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Room).where(Room.owner_id == owner_id).order_by(Room.created_at)
                )
                return [_row_to_dict(r) for r in result.scalars().all()]
        except Exception as e:
            logger.error("rooms_get_failed", error=str(e), owner_id=owner_id)
            return []

    async def get_rooms_by_owner_with_devices(self, owner_id: str) -> List[Dict[str, Any]]:
        rooms = await self.get_rooms_by_owner(owner_id)
        for room in rooms:
            devices = await self.get_devices_by_room(room["id"])
            room["devices"] = devices
            room["total_devices_count"] = len(devices)
            room["active_devices_count"] = sum(1 for d in devices if d.get("state") == "on")
        return rooms

    async def update_room(self, room_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.room import Room
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Room).where(Room.id == room_id))
            room = result.scalar_one_or_none()
            if not room:
                return {}
            for k, v in updates.items():
                if hasattr(room, k):
                    setattr(room, k, v)
            await db.commit()
            await db.refresh(room)
            return _row_to_dict(room)

    async def delete_room(self, room_id: str) -> bool:
        from app.models.room import Room
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Room).where(Room.id == room_id))
                room = result.scalar_one_or_none()
                if room:
                    await db.delete(room)
                    await db.commit()
                return True
        except Exception as e:
            logger.error("room_delete_failed", error=str(e), room_id=room_id)
            return False

    # ── Devices ──────────────────────────────────────────────

    async def create_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.device import Device
        async with AsyncSessionLocal() as db:
            device = Device(**{k: v for k, v in device_data.items() if hasattr(Device, k)})
            db.add(device)
            await db.commit()
            await db.refresh(device)
            logger.info("device_created", device_id=device_data.get("device_id"))
            return _row_to_dict(device)

    async def get_device_by_device_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        from app.models.device import Device
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Device).where(Device.device_id == device_id))
                device = result.scalar_one_or_none()
                return _row_to_dict(device) if device else None
        except Exception as e:
            logger.error("device_get_failed", error=str(e), device_id=device_id)
            return None

    async def get_device_by_uuid(self, uuid: str) -> Optional[Dict[str, Any]]:
        from app.models.device import Device
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Device).where(Device.id == uuid))
                device = result.scalar_one_or_none()
                return _row_to_dict(device) if device else None
        except Exception as e:
            logger.error("device_get_failed", error=str(e), id=uuid)
            return None

    async def get_devices_by_room(self, room_id: str) -> List[Dict[str, Any]]:
        from app.models.device import Device
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Device).where(Device.room_id == room_id))
                return [_row_to_dict(d) for d in result.scalars().all()]
        except Exception as e:
            logger.error("devices_get_failed", error=str(e), room_id=room_id)
            return []

    async def get_all_devices(self, room_id: str | None = None,
                               device_type: str | None = None,
                               is_online: bool | None = None) -> List[Dict[str, Any]]:
        from app.models.device import Device
        try:
            async with AsyncSessionLocal() as db:
                q = select(Device)
                if room_id:
                    q = q.where(Device.room_id == room_id)
                if device_type:
                    q = q.where(Device.device_type == device_type)
                if is_online is not None:
                    q = q.where(Device.is_online == is_online)
                result = await db.execute(q)
                return [_row_to_dict(d) for d in result.scalars().all()]
        except Exception as e:
            logger.error("devices_get_failed", error=str(e))
            return []

    async def resolve_device(self, device_id_or_name: str) -> Optional[Dict[str, Any]]:
        """Resolve device by device_id, name, or fuzzy match."""
        if not device_id_or_name:
            return None

        # 1. Exact device_id
        dev = await self.get_device_by_device_id(device_id_or_name)
        if dev:
            return dev

        # 2. Case-insensitive device_id
        from app.models.device import Device
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Device).where(func.lower(Device.device_id) == device_id_or_name.lower())
                )
                device = result.scalar_one_or_none()
                if device:
                    return _row_to_dict(device)
        except Exception:
            pass

        # 3. Name match
        clean_name = device_id_or_name.lower().replace("-", " ").replace("_", " ").strip()
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Device).where(func.lower(Device.name).contains(clean_name))
                )
                device = result.scalars().first()
                if device:
                    return _row_to_dict(device)
        except Exception:
            pass

        # 4. Fuzzy match via all devices
        all_devs = await self.get_all_devices()
        term_map = {
            "light": "light", "lampu": "light", "lamp": "light",
            "ac": "ac", "aircond": "ac", "pendingin": "ac",
            "tv": "tv", "television": "tv", "televisi": "tv",
            "fan": "fan", "kipas": "fan",
            "curtain": "curtain", "tirai": "curtain", "gorden": "curtain",
            "speaker": "speaker", "soundbar": "speaker",
            "projector": "projector", "proyektor": "projector",
        }
        room_map = {
            "kamar": "kamar", "bedroom": "kamar", "tidur": "kamar",
            "tamu": "ruang-tamu", "living": "ruang-tamu", "keluarga": "ruang-tamu",
            "dapur": "dapur", "kitchen": "dapur",
            "rapat": "ruang-rapat", "meeting": "ruang-rapat", "office": "ruang-rapat",
        }
        tokens = set(re.findall(r"[a-zA-Z0-9]+", device_id_or_name.lower()))
        mapped_types = {term_map[t] for t in tokens if t in term_map}
        mapped_rooms = {room_map[t] for t in tokens if t in room_map}

        # Enrich devices with room slug
        rooms_cache: Dict[str, Dict] = {}
        for d in all_devs:
            rid = d.get("room_id", "")
            if rid and rid not in rooms_cache:
                r = await self.get_room_by_id(rid)
                rooms_cache[rid] = r or {}
            d["_room"] = rooms_cache.get(rid, {})

        if mapped_types and mapped_rooms:
            for d in all_devs:
                r_slug = d["_room"].get("slug", "")
                if d.get("device_type") in mapped_types and r_slug in mapped_rooms:
                    return d

        if mapped_types:
            matching = [d for d in all_devs if d.get("device_type") in mapped_types]
            if len(matching) == 1:
                return matching[0]

        # Substring match
        for d in all_devs:
            d_name = d.get("name", "").lower()
            if clean_name in d_name or d_name in clean_name:
                return d

        return None

    async def update_device_by_device_id(self, device_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.device import Device
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Device).where(Device.device_id == device_id))
            device = result.scalar_one_or_none()
            if not device:
                return {}
            for k, v in updates.items():
                if hasattr(device, k) and k not in ("id", "device_id"):
                    setattr(device, k, v)
            await db.commit()
            await db.refresh(device)
            return _row_to_dict(device)

    async def update_device(self, uuid: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.device import Device
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Device).where(Device.id == uuid))
            device = result.scalar_one_or_none()
            if not device:
                return {}
            for k, v in updates.items():
                if hasattr(device, k) and k not in ("id",):
                    setattr(device, k, v)
            await db.commit()
            await db.refresh(device)
            return _row_to_dict(device)

    async def delete_device(self, device_id: str) -> bool:
        from app.models.device import Device
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Device).where(Device.device_id == device_id))
                device = result.scalar_one_or_none()
                if device:
                    await db.delete(device)
                    await db.commit()
                return True
        except Exception as e:
            logger.error("device_delete_failed", error=str(e), device_id=device_id)
            return False

    # ── Telemetry ────────────────────────────────────────────

    async def log_telemetry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.telemetry import TelemetryLog
        async with AsyncSessionLocal() as db:
            log = TelemetryLog(**{k: v for k, v in data.items() if hasattr(TelemetryLog, k)})
            db.add(log)
            await db.commit()
            await db.refresh(log)
            return _row_to_dict(log)

    async def get_telemetry(self, device_id: str | None = None,
                            limit: int = 100, offset: int = 0) -> tuple[List[Dict], int]:
        from app.models.telemetry import TelemetryLog
        try:
            async with AsyncSessionLocal() as db:
                q = select(TelemetryLog)
                count_q = select(func.count(TelemetryLog.id))
                if device_id:
                    q = q.where(TelemetryLog.device_id == device_id)
                    count_q = count_q.where(TelemetryLog.device_id == device_id)
                q = q.order_by(TelemetryLog.recorded_at.desc()).offset(offset).limit(limit)
                result = await db.execute(q)
                count_result = await db.execute(count_q)
                total = count_result.scalar() or 0
                return [_row_to_dict(r) for r in result.scalars().all()], total
        except Exception as e:
            logger.error("telemetry_get_failed", error=str(e))
            return [], 0

    # ── Command Logs ─────────────────────────────────────────

    async def log_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.command import CommandLog
        async with AsyncSessionLocal() as db:
            log = CommandLog(**{k: v for k, v in data.items() if hasattr(CommandLog, k)})
            db.add(log)
            await db.commit()
            await db.refresh(log)
            return _row_to_dict(log)

    async def get_commands(self, device_id: str | None = None,
                           limit: int = 50, offset: int = 0) -> tuple[List[Dict], int]:
        from app.models.command import CommandLog
        try:
            async with AsyncSessionLocal() as db:
                q = select(CommandLog)
                count_q = select(func.count(CommandLog.id))
                if device_id:
                    q = q.where(CommandLog.device_id == device_id)
                    count_q = count_q.where(CommandLog.device_id == device_id)
                q = q.order_by(CommandLog.executed_at.desc()).offset(offset).limit(limit)
                result = await db.execute(q)
                count_result = await db.execute(count_q)
                total = count_result.scalar() or 0
                return [_row_to_dict(r) for r in result.scalars().all()], total
        except Exception as e:
            logger.error("commands_get_failed", error=str(e))
            return [], 0

    # ── Chat Sessions ────────────────────────────────────────

    async def create_chat_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.chat import ChatSession
        async with AsyncSessionLocal() as db:
            session = ChatSession(**{k: v for k, v in data.items() if hasattr(ChatSession, k)})
            db.add(session)
            await db.commit()
            await db.refresh(session)
            return _row_to_dict(session)

    async def get_chat_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        from app.models.chat import ChatSession
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ChatSession).where(
                        and_(ChatSession.id == session_id, ChatSession.user_id == user_id)
                    )
                )
                session = result.scalar_one_or_none()
                return _row_to_dict(session) if session else None
        except Exception as e:
            logger.error("chat_session_get_failed", error=str(e))
            return None

    async def get_chat_sessions(self, user_id: str, limit: int = 20, offset: int = 0) -> tuple[List[Dict], int]:
        from app.models.chat import ChatSession
        try:
            async with AsyncSessionLocal() as db:
                q = select(ChatSession).where(ChatSession.user_id == user_id)
                count_q = select(func.count(ChatSession.id)).where(ChatSession.user_id == user_id)
                q = q.order_by(ChatSession.updated_at.desc()).offset(offset).limit(limit)
                result = await db.execute(q)
                count_result = await db.execute(count_q)
                total = count_result.scalar() or 0
                return [_row_to_dict(s) for s in result.scalars().all()], total
        except Exception as e:
            logger.error("chat_sessions_get_failed", error=str(e))
            return [], 0

    async def delete_chat_session(self, session_id: str) -> bool:
        from app.models.chat import ChatSession
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
                session = result.scalar_one_or_none()
                if session:
                    await db.delete(session)
                    await db.commit()
                return True
        except Exception as e:
            logger.error("chat_session_delete_failed", error=str(e))
            return False

    # ── Chat Messages ────────────────────────────────────────

    async def create_chat_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.chat import ChatMessage
        async with AsyncSessionLocal() as db:
            msg = ChatMessage(**{k: v for k, v in data.items() if hasattr(ChatMessage, k)})
            db.add(msg)
            await db.commit()
            await db.refresh(msg)
            return _row_to_dict(msg)

    async def get_chat_messages(self, session_id: str) -> List[Dict[str, Any]]:
        from app.models.chat import ChatMessage
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                    .order_by(ChatMessage.created_at)
                )
                return [_row_to_dict(m) for m in result.scalars().all()]
        except Exception as e:
            logger.error("chat_messages_get_failed", error=str(e))
            return []

    # ── Aggregation helpers ──────────────────────────────────

    async def count_rooms(self, owner_id: str | None = None) -> int:
        from app.models.room import Room
        try:
            async with AsyncSessionLocal() as db:
                q = select(func.count(Room.id))
                if owner_id:
                    q = q.where(Room.owner_id == owner_id)
                result = await db.execute(q)
                return result.scalar() or 0
        except Exception:
            return 0

    async def get_system_stats(self) -> Dict[str, Any]:
        from app.models.room import Room
        try:
            devices = await self.get_all_devices()
            total_rooms = await self.count_rooms()

            total_devices = len(devices)
            online = sum(1 for d in devices if d.get("is_online"))
            active = sum(1 for d in devices if (d.get("state") or "").lower() == "on")
            temps = [d["temperature"] for d in devices if d.get("temperature") is not None]
            humids = [d["humidity"] for d in devices if d.get("humidity") is not None]

            return {
                "total_rooms": total_rooms,
                "total_devices": total_devices,
                "online_devices": online,
                "active_devices": active,
                "average_temperature": round(sum(temps) / len(temps), 1) if temps else 24.5,
                "average_humidity": round(sum(humids) / len(humids), 1) if humids else 65.0,
            }
        except Exception as e:
            logger.error("system_stats_failed", error=str(e))
            return {
                "total_rooms": 0, "total_devices": 0, "online_devices": 0,
                "active_devices": 0, "average_temperature": 24.5, "average_humidity": 65.0,
            }

    # ── Schedules ────────────────────────────────────────────

    async def create_schedule(self, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.schedule import Schedule
        async with AsyncSessionLocal() as db:
            schedule = Schedule(**{k: v for k, v in schedule_data.items() if hasattr(Schedule, k)})
            db.add(schedule)
            await db.commit()
            await db.refresh(schedule)
            logger.info("schedule_created", schedule_id=schedule_data.get("id"))
            return _row_to_dict(schedule)

    async def get_schedule_by_id(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        from app.models.schedule import Schedule
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
                schedule = result.scalar_one_or_none()
                return _row_to_dict(schedule) if schedule else None
        except Exception as e:
            logger.error("schedule_get_failed", error=str(e), schedule_id=schedule_id)
            return None

    async def get_user_schedules(self, user_id: str) -> List[Dict[str, Any]]:
        from app.models.schedule import Schedule
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Schedule).where(Schedule.user_id == user_id).order_by(Schedule.created_at)
                )
                return [_row_to_dict(s) for s in result.scalars().all()]
        except Exception as e:
            logger.error("user_schedules_get_failed", error=str(e), user_id=user_id)
            return []

    async def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        from app.models.schedule import Schedule
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
            schedule = result.scalar_one_or_none()
            if not schedule:
                return {}
            for k, v in updates.items():
                if hasattr(schedule, k) and k != "id":
                    setattr(schedule, k, v)
            await db.commit()
            await db.refresh(schedule)
            return _row_to_dict(schedule)

    async def delete_schedule(self, schedule_id: str) -> bool:
        from app.models.schedule import Schedule
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
                schedule = result.scalar_one_or_none()
                if schedule:
                    await db.delete(schedule)
                    await db.commit()
                return True
        except Exception as e:
            logger.error("schedule_delete_failed", error=str(e), schedule_id=schedule_id)
            return False

    async def get_all_schedules(self) -> List[Dict[str, Any]]:
        from app.models.schedule import Schedule
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Schedule))
                return [_row_to_dict(s) for s in result.scalars().all()]
        except Exception as e:
            logger.error("get_all_schedules_failed", error=str(e))
            return []


# Singleton instance — same name as before so all imports still work
supabase_service = MySQLService()

"""
Supabase Service - Primary Database Operations

Single source of truth for all CRUD operations. Every endpoint reads/writes
through this service so data persists in Supabase (not ephemeral SQLite).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from supabase import create_client, Client
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("supabase_service")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SupabaseService:
    """Singleton service for Supabase database operations."""

    def __init__(self):
        self._client: Optional[Client] = None
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
        if not settings.SUPABASE_URL or not key:
            logger.warning("supabase_not_configured",
                         url_set=bool(settings.SUPABASE_URL),
                         key_set=bool(key))
            return
        try:
            # Clean URL: remove trailing /rest/v1/ or / if accidentally passed
            clean_url = re.sub(r"/rest/v1/?$", "", settings.SUPABASE_URL.rstrip("/"))
            self._client = create_client(clean_url, key)
            self._initialized = True
            logger.info("supabase_initialized", url=clean_url)
        except Exception as e:
            logger.error("supabase_init_failed", error=str(e))
            raise

    @property
    def client(self) -> Client:
        if not self._initialized:
            self.initialize()
        if not self._client:
            raise RuntimeError("Supabase client not initialized. Set SUPABASE_URL and SUPABASE_KEY.")
        return self._client

    # ── Users ────────────────────────────────────────────────

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.table("users").insert(user_data).execute()
        logger.info("user_created", user_id=user_data.get("id"))
        return response.data[0] if response.data else {}

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.table("users").select("*").eq("email", email).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("user_get_failed", error=str(e), email=email)
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.table("users").select("*").eq("id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("user_get_failed", error=str(e), user_id=user_id)
            return None

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        updates["updated_at"] = _now()
        response = self.client.table("users").update(updates).eq("id", user_id).execute()
        return response.data[0] if response.data else {}

    # ── Rooms ────────────────────────────────────────────────

    async def create_room(self, room_data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.table("rooms").insert(room_data).execute()
        logger.info("room_created", room_id=room_data.get("id"))
        return response.data[0] if response.data else {}

    async def get_room_by_id(self, room_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.table("rooms").select("*").eq("id", room_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("room_get_failed", error=str(e), room_id=room_id)
            return None

    async def get_room_by_slug(self, slug: str, owner_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.client.table("rooms").select("*")
                .eq("slug", slug).eq("owner_id", owner_id).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("room_get_failed", error=str(e), slug=slug)
            return None

    async def get_rooms_by_owner(self, owner_id: str) -> List[Dict[str, Any]]:
        try:
            response = (
                self.client.table("rooms").select("*")
                .eq("owner_id", owner_id)
                .order("created_at")
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error("rooms_get_failed", error=str(e), owner_id=owner_id)
            return []

    async def get_rooms_by_owner_with_devices(self, owner_id: str) -> List[Dict[str, Any]]:
        """Get rooms with device counts computed."""
        rooms = await self.get_rooms_by_owner(owner_id)
        for room in rooms:
            devices = await self.get_devices_by_room(room["id"])
            room["devices"] = devices
            room["total_devices_count"] = len(devices)
            room["active_devices_count"] = sum(1 for d in devices if d.get("state") == "on")
        return rooms

    async def update_room(self, room_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        updates["updated_at"] = _now()
        response = self.client.table("rooms").update(updates).eq("id", room_id).execute()
        return response.data[0] if response.data else {}

    async def delete_room(self, room_id: str) -> bool:
        try:
            self.client.table("rooms").delete().eq("id", room_id).execute()
            return True
        except Exception as e:
            logger.error("room_delete_failed", error=str(e), room_id=room_id)
            return False

    # ── Devices ──────────────────────────────────────────────

    async def create_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.table("devices").insert(device_data).execute()
        logger.info("device_created", device_id=device_data.get("device_id"))
        return response.data[0] if response.data else {}

    async def get_device_by_device_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device by its device_id string (e.g. 'dev-km-1')."""
        try:
            response = self.client.table("devices").select("*").eq("device_id", device_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("device_get_failed", error=str(e), device_id=device_id)
            return None

    async def get_device_by_uuid(self, uuid: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.table("devices").select("*").eq("id", uuid).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("device_get_failed", error=str(e), id=uuid)
            return None

    async def get_devices_by_room(self, room_id: str) -> List[Dict[str, Any]]:
        try:
            response = self.client.table("devices").select("*").eq("room_id", room_id).execute()
            return response.data or []
        except Exception as e:
            logger.error("devices_get_failed", error=str(e), room_id=room_id)
            return []

    async def get_all_devices(self, room_id: str | None = None,
                               device_type: str | None = None,
                               is_online: bool | None = None) -> List[Dict[str, Any]]:
        """Get all devices with optional filters."""
        try:
            q = self.client.table("devices").select("*")
            if room_id:
                q = q.eq("room_id", room_id)
            if device_type:
                q = q.eq("device_type", device_type)
            if is_online is not None:
                q = q.eq("is_online", is_online)
            response = q.execute()
            return response.data or []
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
        try:
            response = self.client.table("devices").select("*").ilike("device_id", device_id_or_name).execute()
            if response.data:
                return response.data[0]
        except Exception:
            pass

        # 3. Name match
        clean_name = device_id_or_name.lower().replace("-", " ").replace("_", " ").strip()
        try:
            response = self.client.table("devices").select("*").ilike("name", f"%{clean_name}%").execute()
            if response.data:
                return response.data[0]
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
        """Update device by its device_id string."""
        updates["updated_at"] = _now()
        response = self.client.table("devices").update(updates).eq("device_id", device_id).execute()
        return response.data[0] if response.data else {}

    async def update_device(self, uuid: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update device by its UUID primary key."""
        updates["updated_at"] = _now()
        response = self.client.table("devices").update(updates).eq("id", uuid).execute()
        return response.data[0] if response.data else {}

    async def delete_device(self, device_id: str) -> bool:
        """Delete device by device_id string."""
        try:
            self.client.table("devices").delete().eq("device_id", device_id).execute()
            return True
        except Exception as e:
            logger.error("device_delete_failed", error=str(e), device_id=device_id)
            return False

    # ── Telemetry ────────────────────────────────────────────

    async def log_telemetry(self, data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.table("telemetry_logs").insert(data).execute()
        return response.data[0] if response.data else {}

    async def get_telemetry(self, device_id: str | None = None,
                            limit: int = 100, offset: int = 0) -> tuple[List[Dict], int]:
        """Get telemetry logs with count."""
        try:
            q = self.client.table("telemetry_logs").select("*", count="exact")
            if device_id:
                q = q.eq("device_id", device_id)
            q = q.order("recorded_at", desc=True).range(offset, offset + limit - 1)
            response = q.execute()
            return response.data or [], response.count or 0
        except Exception as e:
            logger.error("telemetry_get_failed", error=str(e))
            return [], 0

    # ── Command Logs ─────────────────────────────────────────

    async def log_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.table("command_logs").insert(data).execute()
        return response.data[0] if response.data else {}

    async def get_commands(self, device_id: str | None = None,
                           limit: int = 50, offset: int = 0) -> tuple[List[Dict], int]:
        try:
            q = self.client.table("command_logs").select("*", count="exact")
            if device_id:
                q = q.eq("device_id", device_id)
            q = q.order("executed_at", desc=True).range(offset, offset + limit - 1)
            response = q.execute()
            return response.data or [], response.count or 0
        except Exception as e:
            logger.error("commands_get_failed", error=str(e))
            return [], 0

    # ── Chat Sessions ────────────────────────────────────────

    async def create_chat_session(self, data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.table("chat_sessions").insert(data).execute()
        return response.data[0] if response.data else {}

    async def get_chat_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.client.table("chat_sessions").select("*")
                .eq("id", session_id).eq("user_id", user_id).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("chat_session_get_failed", error=str(e))
            return None

    async def get_chat_sessions(self, user_id: str, limit: int = 20, offset: int = 0) -> tuple[List[Dict], int]:
        try:
            response = (
                self.client.table("chat_sessions").select("*", count="exact")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return response.data or [], response.count or 0
        except Exception as e:
            logger.error("chat_sessions_get_failed", error=str(e))
            return [], 0

    async def delete_chat_session(self, session_id: str) -> bool:
        try:
            self.client.table("chat_sessions").delete().eq("id", session_id).execute()
            return True
        except Exception as e:
            logger.error("chat_session_delete_failed", error=str(e))
            return False

    # ── Chat Messages ────────────────────────────────────────

    async def create_chat_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.table("chat_messages").insert(data).execute()
        return response.data[0] if response.data else {}

    async def get_chat_messages(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            response = (
                self.client.table("chat_messages").select("*")
                .eq("session_id", session_id)
                .order("created_at", desc=False)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error("chat_messages_get_failed", error=str(e))
            return []

    # ── Aggregation helpers ──────────────────────────────────

    async def count_rooms(self, owner_id: str | None = None) -> int:
        try:
            q = self.client.table("rooms").select("id", count="exact")
            if owner_id:
                q = q.eq("owner_id", owner_id)
            response = q.execute()
            return response.count or 0
        except Exception:
            return 0

    async def get_system_stats(self) -> Dict[str, Any]:
        """Aggregate stats for system status endpoint."""
        try:
            devices = await self.get_all_devices()
            rooms_resp = self.client.table("rooms").select("id", count="exact").execute()

            total_devices = len(devices)
            online = sum(1 for d in devices if d.get("is_online"))
            active = sum(1 for d in devices if (d.get("state") or "").lower() == "on")
            temps = [d["temperature"] for d in devices if d.get("temperature") is not None]
            humids = [d["humidity"] for d in devices if d.get("humidity") is not None]

            return {
                "total_rooms": rooms_resp.count or 0,
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
        response = self.client.table("schedules").insert(schedule_data).execute()
        logger.info("schedule_created", schedule_id=schedule_data.get("id"))
        return response.data[0] if response.data else {}

    async def get_schedule_by_id(self, schedule_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.client.table("schedules").select("*").eq("id", schedule_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error("schedule_get_failed", error=str(e), schedule_id=schedule_id)
            return None

    async def get_user_schedules(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            response = (
                self.client.table("schedules")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at")
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            logger.error("user_schedules_get_failed", error=str(e), user_id=user_id)
            return []

    async def update_schedule(self, schedule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        updates["updated_at"] = _now()
        response = self.client.table("schedules").update(updates).eq("id", schedule_id).execute()
        return response.data[0] if response.data else {}

    async def delete_schedule(self, schedule_id: str) -> bool:
        try:
            self.client.table("schedules").delete().eq("id", schedule_id).execute()
            return True
        except Exception as e:
            logger.error("schedule_delete_failed", error=str(e), schedule_id=schedule_id)
            return False

    async def get_all_schedules(self) -> List[Dict[str, Any]]:
        """Get all active schedules."""
        if not self._client:
            return []
        try:
            response = self._client.table("schedules").select("*").execute()
            return response.data if response.data else []
        except Exception as e:
            logger.error("get_all_schedules_failed", error=str(e))
            return []


# Singleton instance
supabase_service = SupabaseService()

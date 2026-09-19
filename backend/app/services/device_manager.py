"""
Device manager service — Supabase primary.

Central business logic for device state management. Bridges API requests,
MQTT commands, Supabase persistence, and WebSocket notifications.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.constants import CommandAction, DeviceState
from app.core.logging import get_logger
from app.services.mqtt_service import mqtt_service
from app.services.websocket_manager import ws_manager
from app.services.supabase_service import supabase_service

logger = get_logger("device_manager")


class DeviceManager:
    """Handles all device-related business logic via Supabase."""

    # ── Device CRUD ──────────────────────────────────────────

    async def list_devices(
        self,
        room_id: str | None = None,
        device_type: str | None = None,
        is_online: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """List devices with optional filters and pagination."""
        all_devs = await supabase_service.get_all_devices(
            room_id=room_id, device_type=device_type, is_online=is_online
        )
        total = len(all_devs)
        start = (page - 1) * page_size
        end = start + page_size
        # Enrich with room info
        rooms_cache: dict[str, dict] = {}
        for d in all_devs:
            rid = d.get("room_id", "")
            if rid and rid not in rooms_cache:
                rooms_cache[rid] = await supabase_service.get_room_by_id(rid) or {}
            d["room"] = rooms_cache.get(rid, {})
        return all_devs[start:end], total

    async def get_device(self, device_id: str) -> dict | None:
        """Get a single device by device_id string or fuzzy match."""
        dev = await supabase_service.resolve_device(device_id)
        if dev and "room" not in dev:
            room = await supabase_service.get_room_by_id(dev.get("room_id", ""))
            dev["room"] = room or {}
        return dev

    async def get_device_by_uuid(self, device_uuid: str) -> dict | None:
        dev = await supabase_service.get_device_by_uuid(device_uuid)
        if dev:
            room = await supabase_service.get_room_by_id(dev.get("room_id", ""))
            dev["room"] = room or {}
        return dev

    async def create_device(self, **kwargs: Any) -> dict:
        dev_id = str(uuid.uuid4()).replace("-", "")
        now = datetime.now(timezone.utc).isoformat()
        device_data = {
            "id": dev_id,
            "device_id": kwargs["device_id"],
            "name": kwargs["name"],
            "device_type": kwargs["device_type"],
            "room_id": str(kwargs["room_id"]) if kwargs.get("room_id") else None,
            "state": kwargs.get("state", "off"),
            "brightness": kwargs.get("brightness"),
            "temperature": kwargs.get("temperature"),
            "humidity": kwargs.get("humidity"),
            "is_online": kwargs.get("is_online", False),
            "firmware_version": kwargs.get("firmware_version"),
            "description": kwargs.get("description"),
            "extra_metadata": kwargs.get("extra_metadata", {}),
            "created_at": now,
            "updated_at": now,
        }
        result = await supabase_service.create_device(device_data)
        logger.info("device_created", device_id=kwargs["device_id"], name=kwargs["name"])
        # Attach room
        if result.get("room_id"):
            result["room"] = await supabase_service.get_room_by_id(result["room_id"]) or {}
        return result

    async def update_device(self, device_id: str, **kwargs: Any) -> dict | None:
        device = await supabase_service.resolve_device(device_id)
        if not device:
            return None
        updates = {k: v for k, v in kwargs.items() if v is not None}
        if not updates:
            return device
        result = await supabase_service.update_device_by_device_id(device["device_id"], updates)
        logger.info("device_updated", device_id=device_id)
        if result.get("room_id"):
            result["room"] = await supabase_service.get_room_by_id(result["room_id"]) or {}
        return result

    async def delete_device(self, device_id: str) -> bool:
        device = await supabase_service.resolve_device(device_id)
        if not device:
            return False
        ok = await supabase_service.delete_device(device["device_id"])
        if ok:
            logger.info("device_deleted", device_id=device_id)
        return ok

    # ── Device Commands ──────────────────────────────────────

    async def send_command(
        self,
        device_id: str,
        action: str,
        value: int | float | str | None = None,
        source: str = "api",
        target_temperature: int | None = None,
        ac_mode: str | None = None,
        fan_speed: int | None = None,
        timer_minutes: int | None = None,
    ) -> dict[str, Any]:
        device = await self.get_device(device_id)
        if not device:
            return {"success": False, "error": f"Device '{device_id}' not found"}

        room = device.get("room", {})
        if not room:
            return {"success": False, "error": f"Device '{device_id}' has no associated room"}

        # Determine target state
        if action == CommandAction.TURN_ON.value:
            target_state = DeviceState.ON.value
        elif action == CommandAction.TURN_OFF.value:
            target_state = DeviceState.OFF.value
        elif action == CommandAction.TOGGLE.value:
            target_state = (
                DeviceState.OFF.value
                if device.get("state") == DeviceState.ON.value
                else DeviceState.ON.value
            )
        elif action == CommandAction.SET_VALUE.value:
            target_state = device.get("state", "off")
        elif action == CommandAction.GET_STATUS.value:
            return {
                "success": True,
                "device_id": device_id,
                "state": device.get("state"),
                "is_online": device.get("is_online"),
                "last_seen_at": device.get("last_seen_at"),
            }
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

        extra: dict[str, Any] = {}
        if value is not None and action == CommandAction.SET_VALUE.value:
            extra["value"] = value
        
        # Add AC/device controls to payload
        if target_temperature is not None:
            extra["target_temperature"] = target_temperature
        if ac_mode is not None:
            extra["ac_mode"] = ac_mode
        if fan_speed is not None:
            extra["fan_speed"] = fan_speed
        if timer_minutes is not None:
            extra["timer_minutes"] = timer_minutes

        # Publish via MQTT
        published = await mqtt_service.publish_command(
            room_slug=room.get("slug", "unknown"),
            device_id=device["device_id"],
            state=target_state,
            extra_payload=extra if extra else None,
        )

        payload_sent = {"state": target_state, "timestamp": int(time.time())}
        if extra:
            payload_sent.update(extra)

        status = "sent" if published else "failed"
        error_msg = None if published else "MQTT publish failed"

        # Log command to Supabase
        cmd_id = str(uuid.uuid4()).replace("-", "")
        now = datetime.now(timezone.utc).isoformat()
        try:
            await supabase_service.log_command({
                "id": cmd_id,
                "device_id": device["device_id"],
                "action": action,
                "payload": payload_sent,
                "source": source,
                "status": status,
                "error_message": error_msg,
                "executed_at": now,
            })
        except Exception:
            pass

        # Update device state in Supabase
        dev_updates: dict[str, Any] = {"state": target_state}
        if action == CommandAction.SET_VALUE.value and value is not None:
            try:
                num_val = float(value)
                if device.get("device_type") == "ac":
                    dev_updates["temperature"] = num_val
                elif device.get("device_type") == "light":
                    dev_updates["brightness"] = int(num_val)
            except (ValueError, TypeError):
                pass
        
        # Update AC controls
        if target_temperature is not None:
            dev_updates["target_temperature"] = target_temperature
        if ac_mode is not None:
            dev_updates["ac_mode"] = ac_mode
        if fan_speed is not None:
            dev_updates["fan_speed"] = fan_speed
        if timer_minutes is not None:
            dev_updates["timer_minutes"] = timer_minutes
            
        try:
            await supabase_service.update_device_by_device_id(device["device_id"], dev_updates)
        except Exception:
            pass

        # Broadcast via WebSocket
        try:
            room_slug = room.get("slug", "unknown")
            extra_ws: dict[str, Any] = {}
            if device.get("brightness") is not None:
                extra_ws["brightness"] = device["brightness"]
            if device.get("temperature") is not None:
                extra_ws["temperature"] = device["temperature"]
            await ws_manager.broadcast_device_status(
                device_id=device["device_id"],
                room_slug=room_slug,
                state=target_state,
                extra=extra_ws if extra_ws else None,
            )
        except Exception:
            pass

        logger.info("device_command_sent", device_id=device["device_id"],
                    action=action, target_state=target_state, published=published)

        return {
            "success": True,
            "device_id": device["device_id"],
            "action": action,
            "payload_sent": payload_sent,
            "status": status,
            "message": f"Command '{action}' sent to {device.get('name', device_id)}",
        }

    # ── Status Update (from MQTT) ────────────────────────────

    async def handle_status_update(
        self, device_id: str, state: str, extra: dict[str, Any] | None = None,
    ) -> None:
        device = await supabase_service.get_device_by_device_id(device_id)
        if not device:
            logger.warning("status_update_unknown_device", device_id=device_id)
            return

        updates: dict[str, Any] = {
            "state": state,
            "is_online": True,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            for key in ("brightness", "temperature", "humidity"):
                if key in extra:
                    updates[key] = extra[key]

        await supabase_service.update_device_by_device_id(device_id, updates)

        room = await supabase_service.get_room_by_id(device.get("room_id", ""))
        room_slug = room.get("slug", "unknown") if room else "unknown"
        await ws_manager.broadcast_device_status(
            device_id=device_id, room_slug=room_slug, state=state, extra=extra
        )

    # ── Telemetry ────────────────────────────────────────────

    async def save_telemetry(
        self,
        device_id: str,
        temperature: float | None = None,
        humidity: float | None = None,
        power_watts: float | None = None,
        extra_data: dict | None = None,
    ) -> dict:
        tel_id = str(uuid.uuid4()).replace("-", "")
        now = datetime.now(timezone.utc).isoformat()

        log = await supabase_service.log_telemetry({
            "id": tel_id,
            "device_id": device_id,
            "temperature": temperature,
            "humidity": humidity,
            "power_watts": power_watts,
            "extra_data": extra_data,
            "recorded_at": now,
        })

        # Update device sensor fields
        try:
            await supabase_service.update_device_by_device_id(device_id, {
                "temperature": temperature,
                "humidity": humidity,
                "is_online": True,
                "last_seen_at": now,
            })
        except Exception:
            pass

        # Broadcast
        await ws_manager.broadcast_telemetry(
            device_id=device_id,
            telemetry={
                "temperature": temperature,
                "humidity": humidity,
                "power_watts": power_watts,
                "recorded_at": now,
            },
        )
        return log

    async def get_telemetry(
        self,
        device_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        return await supabase_service.get_telemetry(device_id=device_id, limit=limit, offset=offset)

    # ── Command Logs ─────────────────────────────────────────

    async def get_command_logs(
        self,
        device_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        return await supabase_service.get_commands(device_id=device_id, limit=limit, offset=offset)


# Module-level singleton
device_manager = DeviceManager()

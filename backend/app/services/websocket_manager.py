"""
WebSocket connection manager for real-time frontend updates.

Maintains active connections per user and broadcasts device state changes,
telemetry data, and AI responses to connected frontend clients.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket

from app.core.constants import WSEventType
from app.core.logging import get_logger

logger = get_logger("websocket_manager")


class ConnectionManager:
    """
    Manages WebSocket connections.

    Supports:
    - Per-user connections (one user may have multiple tabs/devices)
    - Broadcast to all connected clients
    - Targeted send to a specific user
    """

    def __init__(self) -> None:
        # user_id -> list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    @property
    def active_count(self) -> int:
        """Total number of active WebSocket connections."""
        return sum(len(conns) for conns in self._connections.values())

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()

        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = []
            self._connections[user_id].append(websocket)

        logger.info(
            "ws_connected",
            user_id=user_id,
            active_connections=self.active_count,
        )

        # Send acknowledgement
        await self._send_json(websocket, {
            "type": WSEventType.CONNECTION_ACK.value,
            "data": {
                "message": "Connected to SMART AI IoT real-time stream",
                "user_id": user_id,
            },
        })

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a WebSocket connection from the registry."""
        async with self._lock:
            if user_id in self._connections:
                try:
                    self._connections[user_id].remove(websocket)
                except ValueError:
                    pass
                if not self._connections[user_id]:
                    del self._connections[user_id]

        logger.info(
            "ws_disconnected",
            user_id=user_id,
            active_connections=self.active_count,
        )

    async def send_to_user(self, user_id: str, event_type: WSEventType, data: dict[str, Any]) -> None:
        """Send a message to all connections of a specific user."""
        message = {
            "type": event_type.value,
            "data": data,
        }
        async with self._lock:
            connections = self._connections.get(user_id, []).copy()

        stale: list[WebSocket] = []
        for ws in connections:
            success = await self._send_json(ws, message)
            if not success:
                stale.append(ws)

        # Clean up stale connections
        if stale:
            async with self._lock:
                for ws in stale:
                    if user_id in self._connections:
                        try:
                            self._connections[user_id].remove(ws)
                        except ValueError:
                            pass

    async def broadcast(self, event_type: WSEventType, data: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        message = {
            "type": event_type.value,
            "data": data,
        }

        async with self._lock:
            all_connections: list[tuple[str, WebSocket]] = []
            for user_id, connections in self._connections.items():
                for ws in connections:
                    all_connections.append((user_id, ws))

        stale: list[tuple[str, WebSocket]] = []
        for user_id, ws in all_connections:
            success = await self._send_json(ws, message)
            if not success:
                stale.append((user_id, ws))

        # Clean up stale connections
        if stale:
            async with self._lock:
                for user_id, ws in stale:
                    if user_id in self._connections:
                        try:
                            self._connections[user_id].remove(ws)
                        except ValueError:
                            pass

    async def broadcast_device_status(
        self,
        device_id: str,
        room_slug: str,
        state: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Convenience method to broadcast a device status update."""
        data: dict[str, Any] = {
            "device_id": device_id,
            "room": room_slug,
            "state": state,
        }
        if extra:
            data.update(extra)
        await self.broadcast(WSEventType.DEVICE_STATUS_UPDATE, data)

    async def broadcast_telemetry(
        self,
        device_id: str,
        telemetry: dict[str, Any],
    ) -> None:
        """Convenience method to broadcast telemetry data."""
        await self.broadcast(
            WSEventType.TELEMETRY_UPDATE,
            {"device_id": device_id, **telemetry},
        )

    async def _send_json(self, websocket: WebSocket, data: dict[str, Any]) -> bool:
        """Send JSON data to a single WebSocket. Returns False if the connection is stale."""
        try:
            await websocket.send_text(json.dumps(data))
            return True
        except Exception:
            logger.debug("ws_send_failed_stale_connection")
            return False


# Module-level singleton
ws_manager = ConnectionManager()

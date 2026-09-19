"""
WebSocket endpoint for real-time frontend communication.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from jose import JWTError

from app.core.logging import get_logger
from app.core.security import decode_token
from app.services.websocket_manager import ws_manager

logger = get_logger("websocket_endpoint")

router = APIRouter()


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for real-time device updates.

    Connect with: ``ws://host/api/v1/ws?token=<JWT>``

    Events pushed to clients:
    - ``device_status_update``: When a device state changes
    - ``telemetry_update``: New sensor readings
    - ``device_command_sent``: When a command is sent to a device
    - ``ai_response``: AI chat responses (for multi-device views)
    """
    # Validate JWT token
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except JWTError:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Register connection
    await ws_manager.connect(websocket, user_id)

    try:
        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type", "")

                if msg_type == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "data": {},
                    }))
                elif msg_type == "subscribe":
                    # Client can subscribe to specific device updates
                    logger.info(
                        "ws_subscribe",
                        user_id=user_id,
                        target=message.get("data", {}),
                    )
                else:
                    logger.debug(
                        "ws_unknown_message_type",
                        user_id=user_id,
                        msg_type=msg_type,
                    )

            except json.JSONDecodeError:
                logger.warning("ws_invalid_json", user_id=user_id)

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id)
    except Exception as exc:
        logger.exception("ws_error", user_id=user_id, error=str(exc))
        await ws_manager.disconnect(websocket, user_id)

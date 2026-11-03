"""
MQTT message handler bridge — MySQL primary.

Connects incoming MQTT status/telemetry messages to the device manager.
No longer needs SQLAlchemy sessions.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.services.device_manager import device_manager
from app.utils.helpers import parse_mqtt_topic

logger = get_logger("mqtt_handler")


async def handle_device_status(topic: str, payload: dict[str, Any]) -> None:
    """Handle a device status message from MQTT."""
    parsed = parse_mqtt_topic(topic)
    if not parsed:
        logger.warning("mqtt_handler_invalid_topic", topic=topic)
        return

    device_id = parsed["device_id"]
    state = payload.get("state")

    if state not in ("on", "off"):
        logger.warning("mqtt_handler_invalid_state", device_id=device_id, state=state)
        return

    extra: dict[str, Any] = {}
    for key in ("brightness", "temperature", "humidity"):
        if key in payload:
            extra[key] = payload[key]

    try:
        await device_manager.handle_status_update(
            device_id=device_id,
            state=state,
            extra=extra if extra else None,
        )
        logger.info("mqtt_status_processed", device_id=device_id, state=state)
    except Exception as exc:
        logger.exception("mqtt_status_processing_error", device_id=device_id, error=str(exc))


async def handle_device_telemetry(topic: str, payload: dict[str, Any]) -> None:
    """Handle a device telemetry message from MQTT."""
    parsed = parse_mqtt_topic(topic)
    if not parsed:
        logger.warning("mqtt_handler_invalid_telemetry_topic", topic=topic)
        return

    device_id = parsed["device_id"]

    try:
        await device_manager.save_telemetry(
            device_id=device_id,
            temperature=payload.get("temperature"),
            humidity=payload.get("humidity"),
            power_watts=payload.get("power_watts"),
            extra_data={
                k: v for k, v in payload.items()
                if k not in ("temperature", "humidity", "power_watts", "timestamp")
            } or None,
        )
        logger.info("mqtt_telemetry_processed", device_id=device_id)
    except Exception as exc:
        logger.exception("mqtt_telemetry_processing_error", device_id=device_id, error=str(exc))


async def handle_ir_capture(topic: str, payload: dict[str, Any]) -> None:
    """Handle IR frequency capture from hardware sensor."""
    parsed = parse_mqtt_topic(topic)
    if not parsed:
        logger.warning("mqtt_handler_invalid_ir_topic", topic=topic)
        return

    device_id = parsed["device_id"]
    ir_frequency = payload.get("ir_frequency") or payload.get("frequency")
    protocol = payload.get("protocol")
    raw_data = payload.get("raw_data")

    if not ir_frequency:
        logger.warning("mqtt_ir_capture_missing_frequency", device_id=device_id)
        return

    try:
        # Store captured IR data temporarily in WebSocket broadcast
        # Frontend will receive this via WebSocket and display in modal
        from app.services.websocket_manager import ws_manager
        await ws_manager.broadcast_json({
            "type": "ir_captured",
            "device_id": device_id,
            "ir_frequency": ir_frequency,
            "protocol": protocol,
            "raw_data": raw_data,
            "timestamp": payload.get("timestamp")
        })
        logger.info("mqtt_ir_capture_processed", device_id=device_id, protocol=protocol)
    except Exception as exc:
        logger.exception("mqtt_ir_capture_error", device_id=device_id, error=str(exc))

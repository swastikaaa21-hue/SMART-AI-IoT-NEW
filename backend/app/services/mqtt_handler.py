"""
MQTT message handler bridge — Supabase primary.

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

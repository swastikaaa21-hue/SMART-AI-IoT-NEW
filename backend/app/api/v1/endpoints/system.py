"""
System and configuration endpoints — Supabase primary.
"""

from __future__ import annotations

import datetime
from datetime import timezone

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.db.supabase_session import get_db
from app.middleware.auth import get_current_user, get_current_user_optional
from app.schemas.system import (
    SeedResponse,
    SystemConfigResponse,
    SystemConfigUpdate,
    SystemStatusResponse,
    SystemTopicItem,
    SystemTopicsResponse,
)
from app.services.gemini_service import gemini_service
from app.services.mqtt_service import mqtt_service
from app.services.seed_service import seed_user_default_data
from app.services.supabase_service import supabase_service
from app.services.websocket_manager import ws_manager
from app.utils.exceptions import ForbiddenError

router = APIRouter()


def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return "***" if key else ""
    return f"{key[:4]}...{key[-4:]}"


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config(
    user: dict = Depends(get_current_user),
) -> SystemConfigResponse:
    """Retrieve backend system configuration (requires auth, secrets masked)."""
    return SystemConfigResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        app_env=settings.APP_ENV,
        api_v1_prefix=settings.API_V1_PREFIX,
        gemini_api_key=_mask_key(settings.GEMINI_API_KEY),
        gemini_model=settings.GEMINI_MODEL,
        gemini_temperature=settings.GEMINI_TEMPERATURE,
        gemini_max_tokens=settings.GEMINI_MAX_TOKENS,
        gemini_configured=bool(settings.GEMINI_API_KEY and gemini_service._initialised),
        mqtt_broker=settings.MQTT_BROKER,
        mqtt_port=settings.MQTT_PORT,
        mqtt_username=settings.MQTT_USERNAME,
        mqtt_tls_enabled=settings.MQTT_TLS_ENABLED,
        mqtt_connected=mqtt_service.is_connected,
        jwt_access_token_expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.post("/config", response_model=SystemConfigResponse)
async def update_system_config(
    body: SystemConfigUpdate,
    user: dict = Depends(get_current_user),
) -> SystemConfigResponse:
    """Update runtime backend configuration (admin only)."""
    if not user.get("is_superuser", False):
        raise ForbiddenError("Admin privileges required to update configuration")

    if body.gemini_api_key is not None:
        settings.GEMINI_API_KEY = body.gemini_api_key.strip()
    if body.gemini_model is not None:
        settings.GEMINI_MODEL = body.gemini_model.strip()
    if body.gemini_temperature is not None:
        settings.GEMINI_TEMPERATURE = body.gemini_temperature
    if body.gemini_max_tokens is not None:
        settings.GEMINI_MAX_TOKENS = body.gemini_max_tokens
    if body.mqtt_broker is not None:
        settings.MQTT_BROKER = body.mqtt_broker.strip()
    if body.mqtt_port is not None:
        settings.MQTT_PORT = body.mqtt_port
    if body.mqtt_username is not None:
        settings.MQTT_USERNAME = body.mqtt_username.strip()
    if body.mqtt_password is not None:
        settings.MQTT_PASSWORD = body.mqtt_password

    gemini_service.update_config(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        temperature=settings.GEMINI_TEMPERATURE,
        max_tokens=settings.GEMINI_MAX_TOKENS,
    )

    return SystemConfigResponse(
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        app_env=settings.APP_ENV,
        api_v1_prefix=settings.API_V1_PREFIX,
        gemini_api_key=_mask_key(settings.GEMINI_API_KEY),
        gemini_model=settings.GEMINI_MODEL,
        gemini_temperature=settings.GEMINI_TEMPERATURE,
        gemini_max_tokens=settings.GEMINI_MAX_TOKENS,
        gemini_configured=bool(settings.GEMINI_API_KEY and gemini_service._initialised),
        mqtt_broker=settings.MQTT_BROKER,
        mqtt_port=settings.MQTT_PORT,
        mqtt_username=settings.MQTT_USERNAME,
        mqtt_tls_enabled=settings.MQTT_TLS_ENABLED,
        mqtt_connected=mqtt_service.is_connected,
        jwt_access_token_expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    db=Depends(get_db),
    user: dict | None = Depends(get_current_user_optional),
) -> SystemStatusResponse:
    """Get aggregated system statistics."""
    stats = await supabase_service.get_system_stats()

    return SystemStatusResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
        timestamp=datetime.datetime.now(timezone.utc),
        mqtt_connected=mqtt_service.is_connected,
        gemini_ready=gemini_service._initialised,
        ws_active_connections=ws_manager.active_count,
        total_rooms=stats["total_rooms"],
        total_devices=stats["total_devices"],
        online_devices=stats["online_devices"],
        active_devices=stats["active_devices"],
        average_temperature=stats["average_temperature"],
        average_humidity=stats["average_humidity"],
    )


@router.get("/topics", response_model=SystemTopicsResponse)
async def get_system_topics(
    db=Depends(get_db),
    user: dict = Depends(get_current_user),
) -> SystemTopicsResponse:
    """List all MQTT topics for registered devices."""
    devices = await supabase_service.get_all_devices()
    rooms_cache: dict[str, dict] = {}

    topic_items: list[SystemTopicItem] = []
    for d in devices:
        rid = d.get("room_id", "")
        if rid and rid not in rooms_cache:
            rooms_cache[rid] = await supabase_service.get_room_by_id(rid) or {}
        room = rooms_cache.get(rid, {})
        r_slug = room.get("slug", "unknown")

        topic_items.append(SystemTopicItem(
            device_id=d["device_id"],
            name=d["name"],
            room_slug=r_slug,
            command_topic=f"home/{r_slug}/{d['device_id']}/set",
            status_topic=f"home/{r_slug}/{d['device_id']}/status",
            telemetry_topic=f"home/{r_slug}/{d['device_id']}/telemetry",
        ))

    return SystemTopicsResponse(
        broker=settings.MQTT_BROKER,
        port=settings.MQTT_PORT,
        tls=settings.MQTT_TLS_ENABLED,
        status_wildcard="home/+/+/status",
        telemetry_wildcard="home/+/+/telemetry",
        devices=topic_items,
    )


@router.post("/seed", response_model=SeedResponse)
async def seed_data(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> SeedResponse:
    """Seed default rooms and devices for the current user."""
    owner_id = str(user["id"])
    rooms_count, devices_count = await seed_user_default_data(owner_id, reset=False)
    return SeedResponse(
        status="success",
        message=f"Seeded {rooms_count} rooms and {devices_count} devices successfully",
        rooms_count=rooms_count,
        devices_count=devices_count,
    )


@router.post("/reset", response_model=SeedResponse)
async def reset_data(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
) -> SeedResponse:
    """Reset and restore the default dashboard rooms and devices."""
    owner_id = str(user["id"])
    rooms_count, devices_count = await seed_user_default_data(owner_id, reset=True)
    return SeedResponse(
        status="success",
        message="Dashboard restored to initial state",
        rooms_count=rooms_count,
        devices_count=devices_count,
    )

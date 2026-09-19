"""
Telemetry data endpoints — Supabase primary.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.db.supabase_session import get_db
from app.middleware.auth import get_current_user
from app.schemas.common import PaginatedResponse
from app.schemas.telemetry import TelemetryCreate, TelemetryResponse
from app.services.device_manager import device_manager

router = APIRouter()


@router.get("", response_model=PaginatedResponse[TelemetryResponse])
async def list_telemetry(
    device_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Query telemetry logs, optionally filtered by device."""
    offset = (page - 1) * page_size
    logs, total = await device_manager.get_telemetry(
        device_id=device_id, limit=page_size, offset=offset,
    )
    return PaginatedResponse.create(
        items=[TelemetryResponse(**log) for log in logs],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{device_id}", response_model=PaginatedResponse[TelemetryResponse])
async def get_device_telemetry(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get telemetry data for a specific device."""
    offset = (page - 1) * page_size
    logs, total = await device_manager.get_telemetry(
        device_id=device_id, limit=page_size, offset=offset,
    )
    return PaginatedResponse.create(
        items=[TelemetryResponse(**log) for log in logs],
        total=total, page=page, page_size=page_size,
    )


@router.post("", response_model=TelemetryResponse, status_code=201)
async def create_telemetry(
    body: TelemetryCreate,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Manually submit a telemetry reading."""
    log = await device_manager.save_telemetry(
        device_id=body.device_id,
        temperature=body.temperature,
        humidity=body.humidity,
        power_watts=body.power_watts,
        extra_data=body.extra_data,
    )
    return log

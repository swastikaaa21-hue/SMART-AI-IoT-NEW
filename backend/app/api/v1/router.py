"""
Central API router that aggregates all v1 endpoint routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.devices import router as devices_router
from app.api.v1.endpoints.rooms import router as rooms_router
from app.api.v1.endpoints.telemetry import router as telemetry_router
from app.api.v1.endpoints.commands import router as commands_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.voice import router as voice_router
from app.api.v1.endpoints.websocket import router as ws_router
from app.api.v1.endpoints.system import router as system_router
from app.api.v1.endpoints.schedules import router as schedules_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(rooms_router, prefix="/rooms", tags=["Rooms"])
api_router.include_router(devices_router, prefix="/devices", tags=["Devices"])
api_router.include_router(commands_router, prefix="/commands", tags=["Commands"])
api_router.include_router(telemetry_router, prefix="/telemetry", tags=["Telemetry"])
api_router.include_router(chat_router, prefix="/chat", tags=["AI Chat"])
api_router.include_router(voice_router, prefix="/voice", tags=["Voice Assistant"])
api_router.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
api_router.include_router(system_router, prefix="/system", tags=["System & Config"])
api_router.include_router(schedules_router, prefix="/schedules", tags=["Schedules"])

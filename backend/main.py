"""
SMART AI IoT Backend - Main Application Entry Point

This is the central FastAPI application factory that wires together:
- Database engine (SQLite via async SQLAlchemy)
- MQTT service (HiveMQ Cloud on TLS port 8883)
- Google Gemini AI service (Function Calling)
- WebSocket manager (real-time frontend updates)
- API v1 router with all endpoints
- Middleware stack (CORS, auth, logging, error handling)
"""

from __future__ import annotations

import sys
import asyncio

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import get_logger
from app.middleware.error_handler import (
    ErrorHandlerMiddleware,
    RequestLoggingMiddleware,
    register_error_handlers,
)
from app.schemas.common import HealthResponse
from app.services.gemini_service import gemini_service
from app.services.mqtt_handler import handle_device_status, handle_device_telemetry
from app.services.mqtt_service import mqtt_service
from app.services.websocket_manager import ws_manager
from app.services.supabase_service import supabase_service
from app.services.scheduler_service import scheduler_service

logger = get_logger("main")

# ── Rate Limiter ─────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


# ── Application Lifespan ─────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage startup and shutdown of all backend services.

    Startup:
    1. Initialise Gemini AI
    2. Register MQTT message handlers
    3. Connect to HiveMQ Cloud

    Shutdown:
    1. Disconnect MQTT
    2. Clear AI sessions
    """
    logger.info(
        "app_startup",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
    )

    # --- Startup ---
    # 0. Ensure Database tables are created
    try:
        from app.db.session import engine, Base
        import app.models  # noqa: F401
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("db_tables_created")
    except Exception as e:
        logger.warning("db_table_creation_failed", reason=str(e))

    # 1. Initialise Gemini AI
    gemini_service.initialise()
    
    # 2. Initialise Supabase
    try:
        supabase_service.initialize()
    except Exception as e:
        logger.warning("supabase_init_skipped", reason=str(e))

    # 3. Register MQTT message handlers
    mqtt_service.on_status(handle_device_status)
    mqtt_service.on_telemetry(handle_device_telemetry)

    # 4. Connect to MQTT broker (non-fatal if fails)
    try:
        await mqtt_service.connect()
    except Exception as e:
        logger.warning("mqtt_connect_failed", reason=str(e))

    # 5. Start scheduler service
    try:
        await scheduler_service.start()
    except Exception as e:
        logger.warning("scheduler_start_failed", reason=str(e))

    logger.info("app_startup_complete")

    yield

    # --- Shutdown ---
    logger.info("app_shutdown_starting")

    await scheduler_service.stop()
    await mqtt_service.disconnect()
    gemini_service.clear_all_sessions()

    logger.info("app_shutdown_complete")


# ── Application Factory ─────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Central Orchestrator Backend for SMART AI IoT Platform. "
            "Connects Frontend, Database (Supabase), "
            "Broker (HiveMQ Cloud MQTT TLS), and AI (Google Gemini Function Calling)."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- Middleware (order matters: last added = first executed) ---

    # Error handler (outermost)
    application.add_middleware(ErrorHandlerMiddleware)

    # Request logging
    application.add_middleware(RequestLoggingMiddleware)

    # CORS - allow all origins for seamless frontend UI integration across Vercel & local
    cors_origins = list(settings.BACKEND_CORS_ORIGINS) if isinstance(settings.BACKEND_CORS_ORIGINS, list) and settings.BACKEND_CORS_ORIGINS else ["*"]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Custom error handlers
    register_error_handlers(application)

    # --- Routes ---
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Path to frontend UI
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    ui_html_path = frontend_dir / "index.html"

    # --- UI and Health Endpoints ---
    @application.get("/ui", tags=["UI"])
    @application.get("/app", tags=["UI"])
    async def serve_ui():
        """Serve the Smart Home Backend API info page or UI Dashboard if available."""
        if ui_html_path.is_file():
            return FileResponse(str(ui_html_path), media_type="text/html")
        return HTMLResponse(
            "<!DOCTYPE html><html><head><title>SMART AI IoT Backend</title></head>"
            "<body style='font-family:sans-serif;padding:2rem;background:#111;color:#eee;'>"
            "<h1>🤖 SMART AI IoT Backend API</h1>"
            "<p>Backend service running smoothly. (Backend Only Mode)</p>"
            "<p>Interactive API Docs: <a style='color:#38bdf8;' href='/docs'>/docs</a> | Health Check: <a style='color:#38bdf8;' href='/health'>/health</a></p>"
            "</body></html>",
            status_code=200,
        )

    # --- Health Check (outside versioned prefix) ---
    @application.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check():
        """System health check endpoint."""
        return HealthResponse(
            status="ok",
            version=settings.APP_VERSION,
            environment=settings.APP_ENV,
            timestamp=datetime.now(timezone.utc),
            services={
                "mqtt": "connected" if mqtt_service.is_connected else "disconnected",
                "gemini": "ready" if gemini_service._initialised else "not_configured",
                "websocket": f"{ws_manager.active_count} connections",
                "supabase": "connected" if supabase_service._initialized else "not_configured",
            },
        )

    @application.get("/", tags=["Root"])
    async def root(request: Request):
        """Root endpoint - serves UI if HTML requested, otherwise API metadata."""
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header and ui_html_path.is_file():
            return FileResponse(str(ui_html_path), media_type="text/html")

        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs" if settings.DEBUG else "disabled",
            "ui": "/ui",
            "health": "/health",
            "api": settings.API_V1_PREFIX,
        }

    from fastapi.openapi.utils import get_openapi
    def custom_openapi():
        if application.openapi_schema:
            return application.openapi_schema
        openapi_schema = get_openapi(
            title=application.title,
            version=application.version,
            description=application.description,
            routes=application.routes,
        )
        # Force inject the OAuth2 scheme so Swagger UI shows the Authorize button
        openapi_schema["components"] = openapi_schema.get("components", {})
        openapi_schema["components"]["securitySchemes"] = {
            "OAuth2PasswordBearer": {
                "type": "oauth2",
                "flows": {
                    "password": {
                        "scopes": {},
                        "tokenUrl": "/api/v1/auth/login"
                    }
                }
            }
        }
        # Force all routes to require it except public ones
        for path in openapi_schema.get("paths", {}):
            for method in openapi_schema["paths"][path]:
                if path not in ["/api/v1/auth/login", "/api/v1/auth/register", "/health", "/"]:
                    openapi_schema["paths"][path][method]["security"] = [{"OAuth2PasswordBearer": []}]
        application.openapi_schema = openapi_schema
        return application.openapi_schema

    application.openapi = custom_openapi
    return application


# Create the application instance
app = create_app()

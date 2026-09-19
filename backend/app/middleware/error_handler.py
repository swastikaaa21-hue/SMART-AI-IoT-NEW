"""
Global error handling middleware.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger("error_handler")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions and returns structured JSON error responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            import traceback
            traceback.print_exc()
            logger.exception(
                "unhandled_exception",
                path=request.url.path,
                method=request.method,
                error=str(exc),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"Internal server error: {str(exc)}",
                    "error_code": "INTERNAL_ERROR",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs request duration and basic metadata."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            client=request.client.host if request.client else "unknown",
        )
        return response


def register_error_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI app."""

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        return JSONResponse(
            status_code=404,
            content={
                "detail": "Resource not found",
                "error_code": "NOT_FOUND",
                "path": request.url.path,
            },
        )

    @app.exception_handler(422)
    async def validation_handler(request: Request, exc):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Validation error",
                "error_code": "VALIDATION_ERROR",
                "errors": exc.errors() if hasattr(exc, "errors") else str(exc),
            },
        )

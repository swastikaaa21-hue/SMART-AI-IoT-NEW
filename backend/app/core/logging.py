"""
Structured logging configuration using structlog.

Produces JSON logs in production and coloured console output in development.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import settings


def _setup_structlog() -> None:
    """Configure structlog processors and stdlib integration."""

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.LOG_FORMAT == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Quiet noisy third-party loggers
    for name in ("uvicorn.access", "aiomqtt", "httpx", "asyncpg"):
        logging.getLogger(name).setLevel(logging.WARNING)


_setup_structlog()


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structured logger bound with the given name."""
    return structlog.get_logger(name or "app")

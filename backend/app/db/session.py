"""
Async SQLAlchemy engine and session factory for MySQL (TiDB Cloud / MySQL).
"""

from __future__ import annotations

import ssl
from collections.abc import AsyncGenerator

import certifi
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Fix SQLAlchemy 2.0 aiomysql pool_pre_ping signature bug
from sqlalchemy.dialects.mysql.aiomysql import AsyncAdapt_aiomysql_connection
_orig_ping = AsyncAdapt_aiomysql_connection.ping
AsyncAdapt_aiomysql_connection.ping = lambda self, reconnect=True: _orig_ping(self, reconnect)

connect_args: dict = {}
if "tidbcloud.com" in settings.DATABASE_URL or "ssl" in settings.DATABASE_URL:
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    connect_args["ssl"] = ssl_ctx

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG and not settings.is_production,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

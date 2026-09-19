"""
Supabase-only Database Session

Replaces SQLAlchemy with direct Supabase client access.
All operations now use Supabase as the single source of truth.
"""

from __future__ import annotations

from typing import AsyncGenerator
from app.services.supabase_service import supabase_service


async def get_supabase():
    """Dependency injection for Supabase client."""
    return supabase_service.client


# Legacy compatibility - returns None since we don't use SQLAlchemy anymore
async def get_db() -> AsyncGenerator[None, None]:
    """
    Legacy database dependency - kept for backwards compatibility.
    Returns None since all operations now use Supabase directly.
    """
    yield None

"""API dependencies."""

from app.db.session import get_db
from app.middleware.auth import get_current_user

__all__ = ["get_db", "get_current_user"]

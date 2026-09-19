"""
Authentication dependency for FastAPI.

Extracts and validates JWT tokens from the Authorization header.
Now using Supabase as the primary database.
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from app.core.security import decode_token
from app.db.supabase_session import get_db
from app.services.supabase_service import supabase_service
from app.utils.exceptions import UnauthorizedError

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True,
)

oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db = Depends(get_db),
) -> dict:
    """
    FastAPI dependency that extracts the current user from the JWT token.

    Usage::

        @router.get("/me")
        async def me(user: dict = Depends(get_current_user)):
            return user
    """
    try:
        payload = decode_token(token)
    except JWTError:
        raise UnauthorizedError("Invalid or expired token")

    token_type = payload.get("type")
    if token_type != "access":
        raise UnauthorizedError("Invalid token type")

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError("Token missing subject claim")

    user = await supabase_service.get_user_by_id(user_id_str)

    if not user:
        raise UnauthorizedError("User not found")

    if not user.get("is_active", True):
        raise UnauthorizedError("User account is deactivated")

    return user


async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
    db = Depends(get_db),
) -> dict | None:
    """
    Optional authentication dependency.

    Returns the user if a valid token is present, or None otherwise.
    """
    if not token:
        return None

    try:
        return await get_current_user(token=token, db=db)
    except UnauthorizedError:
        return None


async def get_superuser(
    user: dict = Depends(get_current_user),
) -> dict:
    """Dependency that requires superuser privileges."""
    if not user.get("is_superuser", False):
        from app.utils.exceptions import ForbiddenError
        raise ForbiddenError("Superuser privileges required")
    return user

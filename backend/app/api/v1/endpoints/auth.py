"""
Authentication endpoints: register, login, refresh, me.
Now using Supabase as the primary database.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.supabase_session import get_db
from app.middleware.auth import get_current_user
from app.schemas.user import (
    TokenRefreshRequest,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.utils.exceptions import (
    AlreadyExistsError,
    UnauthorizedError,
)
from app.services.supabase_service import supabase_service

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: UserCreate,
    db = Depends(get_db),
):
    """Register a new user account."""
    # Check for existing email
    existing = await supabase_service.get_user_by_email(body.email)
    if existing:
        raise AlreadyExistsError("User", body.email)

    user_id = str(uuid.uuid4()).replace("-", "")
    now = datetime.now(timezone.utc).isoformat()
    
    user_data = {
        "id": user_id,
        "email": body.email,
        "hashed_password": hash_password(body.password),
        "full_name": body.full_name,
        "is_active": True,
        "is_superuser": False,
        "created_at": now,
        "updated_at": now,
    }
    
    created_user = await supabase_service.create_user(user_data)
    return UserResponse(**created_user)


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db = Depends(get_db),
) -> dict:
    """Authenticate a user and return JWT tokens (Supports Swagger UI)."""
    user = await supabase_service.get_user_by_email(form_data.username)

    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise UnauthorizedError("Invalid email or password")

    if not user.get("is_active", True):
        raise UnauthorizedError("Account is deactivated")

    access_token = create_access_token(
        subject=str(user["id"]),
        extra_claims={"email": user["email"]},
    )
    refresh_token = create_refresh_token(subject=str(user["id"]))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: TokenRefreshRequest,
    db = Depends(get_db),
) -> dict:
    """Refresh an access token using a valid refresh token."""
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise UnauthorizedError("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Token is not a refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    user = await supabase_service.get_user_by_id(user_id)

    if not user or not user.get("is_active", True):
        raise UnauthorizedError("User not found or deactivated")

    access_token = create_access_token(
        subject=str(user["id"]),
        extra_claims={"email": user["email"]},
    )
    new_refresh_token = create_refresh_token(subject=str(user["id"]))

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: dict = Depends(get_current_user),
) -> UserResponse:
    """Get the current authenticated user's profile."""
    return UserResponse(**user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    user: dict = Depends(get_current_user),
    db = Depends(get_db),
):
    """Update the current user's profile."""
    updates = {}
    
    if body.email and body.email != user["email"]:
        existing = await supabase_service.get_user_by_email(body.email)
        if existing:
            raise AlreadyExistsError("User", body.email)
        updates["email"] = body.email

    if body.full_name is not None:
        updates["full_name"] = body.full_name

    if body.password:
        updates["hashed_password"] = hash_password(body.password)

    if updates:
        updated_user = await supabase_service.update_user(user["id"], updates)
        return UserResponse(**updated_user)
    
    return UserResponse(**user)


@router.post("/verify-password")
async def verify_user_password(
    password: str,
    user: dict = Depends(get_current_user),
) -> dict:
    """Verify user password for showing in settings."""
    if verify_password(password, user["hashed_password"]):
        return {"verified": True}
    raise UnauthorizedError("Invalid password")

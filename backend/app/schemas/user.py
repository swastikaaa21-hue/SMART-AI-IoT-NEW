"""
User and authentication schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str | uuid.UUID
    email: str
    full_name: str | None = None
    home_name: str | None = None
    location: str | None = None
    avatar_url: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefreshRequest(BaseModel):
    refresh_token: str

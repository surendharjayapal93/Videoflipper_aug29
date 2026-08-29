"""Pydantic schemas for the auth module.

Request/response models only - business logic lives in
`app.services.auth_service`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    """Payload for POST /auth/register."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=100)


class UserLogin(BaseModel):
    """Payload for POST /auth/login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public-facing user profile. Never includes `hashed_password`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime


class UserUpdate(BaseModel):
    """Payload for PUT /auth/me. All fields optional (partial update)."""

    full_name: str | None = Field(default=None, max_length=100)


class TokenResponse(BaseModel):
    """Payload returned on successful register/login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Payload for POST /auth/refresh and POST /auth/logout."""

    refresh_token: str

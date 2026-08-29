"""Auth endpoints: register, login, refresh, logout, profile.

Routers stay thin: validation is handled by Pydantic schemas, business
logic lives in `app.services.auth_service`, and errors are raised as
`AppError` subclasses so `app.exceptions` handlers produce a consistent
JSON error shape.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.rate_limit import rate_limit
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from app.services import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# 5 attempts per minute per client IP on the credential-guessing-sensitive routes.
_auth_rate_limit = rate_limit(max_requests=5, window_seconds=60)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_auth_rate_limit)],
)
async def register(data: UserRegister, db: Session = Depends(get_db)) -> TokenResponse:
    """Create a new account and return an initial token pair."""
    user = auth_service.register_user(db, data)
    return auth_service.issue_tokens(db, user)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(_auth_rate_limit)],
)
async def login(data: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    """Verify credentials and return a token pair."""
    user = auth_service.authenticate_user(db, data.email, data.password)
    return auth_service.issue_tokens(db, user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Exchange a valid refresh token for a new token pair."""
    return auth_service.refresh_access_token(db, data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(data: RefreshRequest, db: Session = Depends(get_db)) -> None:
    """Revoke a refresh token, logging the client out."""
    auth_service.revoke_refresh_token(db, data.refresh_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile."""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Update the authenticated user's profile."""
    return auth_service.update_profile(db, current_user, data)

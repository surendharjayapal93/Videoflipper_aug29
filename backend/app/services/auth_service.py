"""Business logic for registration, login, token refresh, and profile updates.

Routers stay thin (validation + response shaping); all DB access and
auth rules for the auth module live here.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC

from sqlalchemy.orm import Session

from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import get_settings
from app.exceptions import ConflictError, UnauthorizedError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenResponse, UserRegister, UserUpdate

logger = logging.getLogger(__name__)

settings = get_settings()


def register_user(db: Session, data: UserRegister) -> User:
    """Create a new user account.

    Raises `ConflictError` if the email is already registered.
    """
    existing = db.query(User).filter(User.email == data.email).first()
    if existing is not None:
        raise ConflictError("An account with this email already exists")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Registered new user id=%s", user.id)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Verify credentials and return the matching active user.

    Raises `UnauthorizedError` for any bad-credential or inactive-account
    case. The message is intentionally generic so it does not reveal
    whether the email exists.
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("Account is inactive")
    return user


def issue_tokens(db: Session, user: User) -> TokenResponse:
    """Create a fresh access/refresh token pair and persist the refresh token."""
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(
        RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=expires_at,
            revoked=False,
        )
    )
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def refresh_access_token(db: Session, refresh_token: str) -> TokenResponse:
    """Exchange a valid, unrevoked refresh token for a new token pair.

    The presented refresh token is revoked and replaced (rotation), which
    limits the damage if a refresh token is ever leaked. Raises
    `UnauthorizedError` if the token is malformed, expired, revoked,
    unknown, or its user is no longer active.
    """
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid refresh token")

    stored = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if stored is None:
        raise UnauthorizedError("Invalid refresh token")
    if stored.revoked:
        raise UnauthorizedError("Refresh token has been revoked")

    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < datetime.now(UTC):
        raise UnauthorizedError("Refresh token has expired")

    user = db.query(User).filter(User.id == stored.user_id).first()
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is inactive")

    # Rotate: revoke the presented token and issue a brand new pair.
    stored.revoked = True
    db.add(stored)
    db.commit()

    return issue_tokens(db, user)


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    """Revoke a refresh token (logout).

    Idempotent: an unknown or already-revoked token is treated as
    already logged out rather than an error, so logout never leaks
    whether a token was valid.
    """
    stored = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if stored is None:
        logger.info("Logout requested for unknown refresh token")
        return

    stored.revoked = True
    db.add(stored)
    db.commit()
    logger.info("Revoked refresh token id=%s for user_id=%s", stored.id, stored.user_id)


def update_profile(db: Session, user: User, data: UserUpdate) -> User:
    """Apply a partial profile update to `user`."""
    if data.full_name is not None:
        user.full_name = data.full_name

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

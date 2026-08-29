"""Password hashing and JWT helpers for the auth module.

Access tokens are short-lived (`ACCESS_TOKEN_EXPIRE_MINUTES`) and used to
authenticate API requests. Refresh tokens are long-lived
(`REFRESH_TOKEN_EXPIRE_DAYS`), are persisted in the `refresh_tokens` table
by `app.services.auth_service`, and can be revoked server-side (logout).

Never log a raw password, hashed password, or token value.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, UTC
from typing import Any, Literal
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    """Encode a JWT with `sub`, `type`, `jti`, and `exp` claims.

    `jti` (a random UUID) guarantees each issued token is unique even
    when multiple tokens are issued for the same user within the same
    second - JWT encoding is otherwise deterministic given identical
    claims, which would otherwise violate the `refresh_tokens.token`
    unique constraint.
    """
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int) -> str:
    """Create a short-lived access token for `user_id`."""
    return _create_token(
        subject=str(user_id),
        token_type="access",
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    """Create a long-lived refresh token for `user_id`.

    The caller (`auth_service`) is responsible for persisting this token
    in the `refresh_tokens` table.
    """
    return _create_token(
        subject=str(user_id),
        token_type="refresh",
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT, returning its payload or `None` on failure.

    Returns `None` for any invalid, malformed, or expired token rather
    than raising, so callers can uniformly translate failures into an
    `UnauthorizedError`.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        logger.info("JWT decode failed: invalid or expired token")
        return None

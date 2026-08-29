"""Shared FastAPI dependencies.

`get_db` is provided by the database module (owned by DATABASE-AGENT).
`get_current_user` resolves the authenticated user from the
`Authorization: Bearer <access_token>` header.
"""

import logging

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.database import get_db  # re-exported for convenience
from app.exceptions import UnauthorizedError
from app.models.user import User

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the currently authenticated user from the `Authorization` header.

    Raises `UnauthorizedError` if the header is missing, the token is
    malformed/expired, it is not an access token, or the user no longer
    exists / is inactive.
    """
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Missing bearer token")

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired access token")

    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedError("Invalid access token")

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise UnauthorizedError("Invalid access token") from None

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")

    return user

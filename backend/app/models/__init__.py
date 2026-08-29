"""SQLAlchemy models.

Import every model module here so `Base.metadata` is fully populated for
Alembic autogenerate and for `Base.metadata.create_all()` in tests.
"""

from app.models.base import Base, TimestampMixin
from app.models.highlight import Highlight, HighlightStatus
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.models.video import FlipDirection, Video, VideoStatus

__all__ = [
    "Base",
    "FlipDirection",
    "Highlight",
    "HighlightStatus",
    "RefreshToken",
    "TimestampMixin",
    "User",
    "Video",
    "VideoStatus",
]

"""Video model."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class FlipDirection(str, enum.Enum):
    """Direction(s) a video should be flipped in."""

    horizontal = "horizontal"
    vertical = "vertical"
    both = "both"


class VideoStatus(str, enum.Enum):
    """Processing lifecycle status of a video job."""

    pending = "pending"
    downloading = "downloading"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Video(Base, TimestampMixin):
    """A flip job submitted by a user for a YouTube video."""

    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    youtube_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    youtube_video_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    flip_direction: Mapped[FlipDirection] = mapped_column(
        Enum(FlipDirection, name="flip_direction"), nullable=False
    )
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus, name="video_status"), default=VideoStatus.pending, nullable=False
    )

    output_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="videos")

    def __repr__(self) -> str:
        return f"<Video id={self.id} user_id={self.user_id} status={self.status}>"

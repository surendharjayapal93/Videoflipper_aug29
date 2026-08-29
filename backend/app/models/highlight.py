"""Highlight model."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class HighlightStatus(str, enum.Enum):
    """Processing lifecycle status of a highlight-generation job."""

    pending = "pending"
    downloading = "downloading"
    analyzing = "analyzing"
    rendering = "rendering"
    completed = "completed"
    failed = "failed"


class Highlight(Base, TimestampMixin):
    """A ~1 minute highlight-reel job generated from a YouTube video."""

    __tablename__ = "highlights"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    youtube_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    youtube_video_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_title: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[HighlightStatus] = mapped_column(
        Enum(HighlightStatus, name="highlight_status"), default=HighlightStatus.pending, nullable=False
    )

    source_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    highlight_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="highlights")

    def __repr__(self) -> str:
        return f"<Highlight id={self.id} user_id={self.user_id} status={self.status}>"

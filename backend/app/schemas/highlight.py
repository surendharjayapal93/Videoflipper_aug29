"""Pydantic schemas for the highlights module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.highlight import HighlightStatus


class HighlightCreate(BaseModel):
    """Payload to submit a new highlight-generation job for a YouTube video."""

    youtube_url: str = Field(..., min_length=1, max_length=2048)

    @field_validator("youtube_url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("youtube_url must not be empty")
        return value


class HighlightResponse(BaseModel):
    """Public representation of a `Highlight` row."""

    id: int
    user_id: int
    youtube_url: str
    youtube_video_id: str
    source_title: str | None
    status: HighlightStatus
    source_duration_seconds: float | None
    highlight_duration_seconds: float | None
    file_size_bytes: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

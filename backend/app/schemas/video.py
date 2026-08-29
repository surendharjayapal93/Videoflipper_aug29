"""Pydantic schemas for the videos module."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.video import VideoStatus

FlipDirectionLiteral = Literal["horizontal", "vertical", "both"]


class VideoCreate(BaseModel):
    """Payload to submit a new flip job for a YouTube video."""

    youtube_url: str = Field(..., min_length=1, max_length=2048)
    flip_direction: FlipDirectionLiteral

    @field_validator("youtube_url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("youtube_url must not be empty")
        return value


class VideoResponse(BaseModel):
    """Public representation of a `Video` row.

    `storage_url` (the location of the raw, un-flipped source download) is
    intentionally omitted: it points at an internal storage path/key that
    clients have no use for and that we don't want to expose. `output_url`
    is also an internal storage key rather than a directly fetchable URL —
    clients should use `GET /api/videos/{id}/download` to retrieve the
    processed file instead of consuming `output_url` directly.
    """

    id: int
    user_id: int
    youtube_url: str
    youtube_video_id: str
    source_title: str | None
    flip_direction: str
    status: VideoStatus
    duration_seconds: float | None
    file_size_bytes: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoListParams(BaseModel):
    """Query parameters accepted by `GET /api/videos`."""

    status: VideoStatus | None = None
    search: str | None = Field(default=None, max_length=500)
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)

"""Pydantic schemas for the dashboard module.

Read-only aggregation views over `Video` rows - there is no dedicated
"dashboard" entity/table.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.video import VideoStatus


class VideoSummary(BaseModel):
    """Minimal video representation used for dashboard recent activity.

    A trimmed-down alternative to `app.schemas.video.VideoResponse` -
    the dashboard's recent-activity list only needs enough to render a
    row (title, status, timestamp), not the full video record.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_title: str | None
    status: VideoStatus
    created_at: datetime


class DashboardStats(BaseModel):
    """Aggregated usage stats for the current user's videos.

    `completed_videos + failed_videos + processing_videos == total_videos`:
    `processing_videos` covers every non-terminal status (`pending`,
    `downloading`, `processing`) so the three buckets are exhaustive.
    """

    model_config = ConfigDict(from_attributes=True)

    total_videos: int
    completed_videos: int
    failed_videos: int
    processing_videos: int
    total_storage_bytes: int
    recent_activity: list[VideoSummary]

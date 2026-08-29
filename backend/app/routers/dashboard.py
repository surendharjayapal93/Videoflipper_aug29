"""Dashboard endpoints: usage stats aggregated from a user's videos.

There is no dedicated dashboard entity - everything here is a read-only
SQL aggregation over `Video` rows scoped to the current user.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.video import Video, VideoStatus
from app.schemas.dashboard import DashboardStats, VideoSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

RECENT_ACTIVITY_LIMIT = 5


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardStats:
    """Return aggregated video stats + recent activity for the current user.

    Counts and the storage sum are computed with a single SQL aggregation
    query (`func.count`/`func.sum` with `CASE` expressions) rather than
    loading every video row into Python, so this stays a fixed number of
    round trips regardless of how many videos the user has.
    """
    aggregates = db.execute(
        select(
            func.count(Video.id).label("total_videos"),
            func.coalesce(
                func.sum(case((Video.status == VideoStatus.completed, 1), else_=0)),
                0,
            ).label("completed_videos"),
            func.coalesce(
                func.sum(case((Video.status == VideoStatus.failed, 1), else_=0)),
                0,
            ).label("failed_videos"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            Video.status.notin_([VideoStatus.completed, VideoStatus.failed]),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("processing_videos"),
            func.coalesce(func.sum(Video.file_size_bytes), 0).label("total_storage_bytes"),
        ).where(Video.user_id == current_user.id)
    ).one()

    recent_videos = (
        db.execute(
            select(Video)
            .where(Video.user_id == current_user.id)
            .order_by(Video.created_at.desc())
            .limit(RECENT_ACTIVITY_LIMIT)
        )
        .scalars()
        .all()
    )

    logger.info(
        "Computed dashboard stats for user_id=%s: total=%s completed=%s failed=%s processing=%s",
        current_user.id,
        aggregates.total_videos,
        aggregates.completed_videos,
        aggregates.failed_videos,
        aggregates.processing_videos,
    )

    return DashboardStats(
        total_videos=aggregates.total_videos,
        completed_videos=aggregates.completed_videos,
        failed_videos=aggregates.failed_videos,
        processing_videos=aggregates.processing_videos,
        total_storage_bytes=aggregates.total_storage_bytes,
        recent_activity=[VideoSummary.model_validate(video) for video in recent_videos],
    )

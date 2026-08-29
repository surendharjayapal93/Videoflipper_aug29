"""Video flip job endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.video import VideoStatus
from app.schemas.video import VideoCreate, VideoListParams, VideoResponse
from app.services import video_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("", response_model=VideoResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_video(
    payload: VideoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoResponse:
    """Submit a YouTube URL for flipping. Validates the URL synchronously
    and schedules the download/flip pipeline to run in the background.
    """
    video = video_service.create_video_job(db, background_tasks, current_user.id, payload)
    return VideoResponse.model_validate(video)


@router.get("", response_model=list[VideoResponse])
async def list_videos(
    status_filter: VideoStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=500),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[VideoResponse]:
    """List the current user's video jobs, optionally filtered by status
    and/or a search term matched against the source title.
    """
    params = VideoListParams(status=status_filter, search=search, skip=skip, limit=limit)
    videos = video_service.list_videos(db, current_user.id, params)
    return [VideoResponse.model_validate(v) for v in videos]


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoResponse:
    """Fetch a single video job belonging to the current user."""
    video = video_service.get_video_for_user(db, current_user.id, video_id)
    return VideoResponse.model_validate(video)


@router.get("/{video_id}/download")
async def download_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Stream the flipped output file for a completed video job."""
    video = video_service.get_video_for_user(db, current_user.id, video_id)
    output_path = video_service.get_download_path(video)
    filename = f"{video.youtube_video_id}_{video.flip_direction.value}.mp4"
    return FileResponse(path=output_path, media_type="video/mp4", filename=filename)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a video job's DB row and its stored source/output files."""
    video = video_service.get_video_for_user(db, current_user.id, video_id)
    video_service.delete_video(db, video)

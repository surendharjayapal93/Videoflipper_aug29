"""Highlight-reel generation endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.highlight import HighlightCreate, HighlightResponse
from app.services import highlight_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/highlights", tags=["highlights"])


@router.post("", response_model=HighlightResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_highlight(
    payload: HighlightCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HighlightResponse:
    """Submit a YouTube URL to generate a ~1 minute highlight reel.

    Validates the URL synchronously and schedules the download/analyze/
    render pipeline to run in the background.
    """
    highlight = highlight_service.create_highlight_job(db, background_tasks, current_user.id, payload)
    return HighlightResponse.model_validate(highlight)


@router.get("/{highlight_id}", response_model=HighlightResponse)
async def get_highlight(
    highlight_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HighlightResponse:
    """Fetch a single highlight job belonging to the current user."""
    highlight = highlight_service.get_highlight_for_user(db, current_user.id, highlight_id)
    return HighlightResponse.model_validate(highlight)


@router.get("/{highlight_id}/download")
async def download_highlight(
    highlight_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Stream the completed highlight reel file."""
    highlight = highlight_service.get_highlight_for_user(db, current_user.id, highlight_id)
    output_path = highlight_service.get_download_path(highlight)
    filename = f"{highlight.youtube_video_id}_highlight.mp4"
    return FileResponse(path=output_path, media_type="video/mp4", filename=filename)

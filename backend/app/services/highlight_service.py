"""Orchestration for the highlight-reel generation pipeline.

Mirrors `video_service.py`'s job lifecycle pattern (validate -> pending row
-> `BackgroundTasks` pipeline -> terminal status), reusing the same
YouTube download/validation and storage building blocks. Deliberately does
not wire into the Video model's watchdog/retention/dedup machinery -- this
is a smaller, standalone MVP feature; the same protections can be
extended here later if it needs them.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.exceptions import ConflictError, NotFoundError
from app.models.highlight import Highlight, HighlightStatus
from app.schemas.highlight import HighlightCreate
from app.services import highlight_extraction
from app.services.storage import get_storage_backend
from app.services.youtube_downloader import download_video, validate_youtube_url

logger = logging.getLogger(__name__)


def _output_key(highlight_id: int) -> str:
    return f"highlights/{highlight_id}/output.mp4"


def create_highlight_job(
    db: Session, background_tasks: BackgroundTasks, user_id: int, payload: HighlightCreate
) -> Highlight:
    """Validate the submitted URL, create a pending `Highlight` row, and
    schedule background processing.
    """
    youtube_video_id = validate_youtube_url(payload.youtube_url)

    highlight = Highlight(
        user_id=user_id,
        youtube_url=payload.youtube_url,
        youtube_video_id=youtube_video_id,
        status=HighlightStatus.pending,
    )
    db.add(highlight)
    db.commit()
    db.refresh(highlight)

    logger.info(
        "Created highlight job id=%s user_id=%s youtube_video_id=%s",
        highlight.id,
        user_id,
        youtube_video_id,
    )
    background_tasks.add_task(process_highlight_job, highlight.id)
    return highlight


def process_highlight_job(highlight_id: int) -> None:
    """Run the full download -> analyze -> render -> store pipeline for `highlight_id`.

    Opens its own DB session since it runs outside the request lifecycle.
    Any exception along the way is caught and recorded as status=failed
    with `error_message` set, so the job never gets stuck in an
    in-progress state.
    """
    db = SessionLocal()
    storage = get_storage_backend()
    try:
        highlight = db.query(Highlight).filter(Highlight.id == highlight_id).first()
        if highlight is None:
            logger.error("process_highlight_job: highlight id=%s not found", highlight_id)
            return

        try:
            with tempfile.TemporaryDirectory(prefix=f"highlight_{highlight_id}_") as tmp_dir:
                tmp_path = Path(tmp_dir)
                source_path = tmp_path / "source.mp4"
                output_path = tmp_path / "output.mp4"

                highlight.status = HighlightStatus.downloading
                db.commit()

                metadata = download_video(highlight.youtube_url, source_path)
                highlight.source_title = str(metadata.get("title") or "") or None
                highlight.status = HighlightStatus.analyzing
                db.commit()

                total_duration = highlight_extraction.probe_duration_seconds(source_path)
                highlight.source_duration_seconds = total_duration

                active_segments = highlight_extraction.detect_active_segments(source_path, total_duration)
                selected_segments = highlight_extraction.select_highlight_segments(
                    active_segments, total_duration
                )

                highlight.status = HighlightStatus.rendering
                db.commit()

                highlight_extraction.render_highlight_reel(source_path, selected_segments, output_path)

                highlight.output_url = storage.save(_output_key(highlight_id), output_path)
                highlight.highlight_duration_seconds = sum(seg.duration for seg in selected_segments)
                highlight.file_size_bytes = output_path.stat().st_size
                highlight.status = HighlightStatus.completed
                db.commit()

            logger.info("Highlight job id=%s completed", highlight_id)

        except Exception as exc:
            logger.exception("Highlight job id=%s failed", highlight_id)
            db.rollback()
            highlight = db.query(Highlight).filter(Highlight.id == highlight_id).first()
            if highlight is not None:
                highlight.status = HighlightStatus.failed
                highlight.error_message = str(exc)[:2000]
                db.commit()
    finally:
        db.close()


def get_highlight_for_user(db: Session, user_id: int, highlight_id: int) -> Highlight:
    """Fetch a highlight job by id, scoped to `user_id`. Raises `NotFoundError` otherwise."""
    highlight = (
        db.query(Highlight)
        .filter(Highlight.id == highlight_id, Highlight.user_id == user_id)
        .first()
    )
    if highlight is None:
        raise NotFoundError("Highlight not found")
    return highlight


def get_download_path(highlight: Highlight) -> Path:
    """Resolve the local filesystem path of a completed highlight's output file."""
    if highlight.status != HighlightStatus.completed:
        raise ConflictError("Highlight is not ready for download")

    storage = get_storage_backend()
    path = storage.resolve_path(_output_key(highlight.id))
    if not path.exists():
        raise NotFoundError("Output file not found")
    return path

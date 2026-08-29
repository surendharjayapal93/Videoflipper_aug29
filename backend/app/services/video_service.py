"""Orchestration for the video flip pipeline.

`create_video_job` runs synchronously inside the request (URL validation +
DB row creation) and schedules `process_video_job` via FastAPI
`BackgroundTasks`. `process_video_job` runs after the response has been
sent, so it opens its own DB session rather than reusing the
request-scoped one.

No Celery/Redis here by design (MVP scope) — `BackgroundTasks` is enough
for a single-process deployment; if throughput ever requires a real queue,
`process_video_job`'s body can move into a worker task largely unchanged.
"""

from __future__ import annotations

import logging
import tempfile
from datetime import datetime, timedelta, UTC
from pathlib import Path

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.exceptions import ConflictError, NotFoundError
from app.models.video import FlipDirection, Video, VideoStatus
from app.schemas.video import VideoCreate, VideoListParams
from app.services import video_processing
from app.services.storage import get_storage_backend
from app.services.youtube_downloader import download_video, validate_youtube_url

logger = logging.getLogger(__name__)

# Non-terminal statuses a job can be "stuck" in.
_ACTIVE_STATUSES = (VideoStatus.pending, VideoStatus.downloading, VideoStatus.processing)


def _source_key(video_id: int) -> str:
    return f"{video_id}/source.mp4"


def _output_key(video_id: int) -> str:
    return f"{video_id}/output.mp4"


def create_video_job(db: Session, background_tasks: BackgroundTasks, user_id: int, payload: VideoCreate) -> Video:
    """Validate the submitted URL, create a pending `Video` row, and
    schedule background processing.

    Refuses (409 Conflict) to create a duplicate job if the same user
    already has one active (pending/downloading/processing) for the same
    video + flip direction — without this, a double-clicked submit button
    or a resubmitted link spins up unlimited parallel jobs that each
    independently re-download and re-encode the same source, for no
    benefit (a genuinely different flip direction on the same video is a
    different job and isn't blocked). This is a plain app-level check, not
    a DB constraint: the tiny window between two near-simultaneous
    requests both passing the check is an acceptable risk for what's
    fundamentally a UX safeguard against accidental duplicates, not a
    data-integrity invariant.
    """
    youtube_video_id = validate_youtube_url(payload.youtube_url)
    flip_direction = FlipDirection(payload.flip_direction)

    duplicate = (
        db.query(Video)
        .filter(
            Video.user_id == user_id,
            Video.youtube_video_id == youtube_video_id,
            Video.flip_direction == flip_direction,
            Video.status.in_(_ACTIVE_STATUSES),
        )
        .first()
    )
    if duplicate is not None:
        raise ConflictError(
            "This video is already queued or processing with this flip direction. "
            "Wait for it to finish, or check your video list."
        )

    video = Video(
        user_id=user_id,
        youtube_url=payload.youtube_url,
        youtube_video_id=youtube_video_id,
        flip_direction=flip_direction,
        status=VideoStatus.pending,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    logger.info("Created video job id=%s user_id=%s youtube_video_id=%s", video.id, user_id, youtube_video_id)
    background_tasks.add_task(process_video_job, video.id)
    return video


def process_video_job(video_id: int) -> None:
    """Run the full download -> flip -> store pipeline for `video_id`.

    Opens its own DB session since it runs outside the request lifecycle.
    Any exception along the way is caught and recorded as status=failed
    with `error_message` set, so the job never gets stuck in an
    in-progress state.
    """
    db = SessionLocal()
    storage = get_storage_backend()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if video is None:
            logger.error("process_video_job: video id=%s not found", video_id)
            return

        try:
            with tempfile.TemporaryDirectory(prefix=f"videoflipper_{video_id}_") as tmp_dir:
                tmp_path = Path(tmp_dir)
                source_path = tmp_path / "source.mp4"
                output_path = tmp_path / "output.mp4"

                video.status = VideoStatus.downloading
                db.commit()

                metadata = download_video(video.youtube_url, source_path)

                video.source_title = str(metadata.get("title") or "") or None
                video.duration_seconds = metadata.get("duration_seconds")
                video.status = VideoStatus.processing
                db.commit()

                video_processing.flip_video(source_path, output_path, video.flip_direction.value)

                # The downloaded source is never served to users (only the
                # flipped output is) and is deleted automatically when this
                # `TemporaryDirectory` block exits below — deliberately not
                # copied into permanent storage, so per-job disk usage is
                # roughly half of what it'd otherwise be.
                video.output_url = storage.save(_output_key(video_id), output_path)
                video.file_size_bytes = output_path.stat().st_size
                video.status = VideoStatus.completed
                db.commit()

            logger.info("Video job id=%s completed", video_id)

        except Exception as exc:
            logger.exception("Video job id=%s failed", video_id)
            db.rollback()
            video = db.query(Video).filter(Video.id == video_id).first()
            if video is not None:
                video.status = VideoStatus.failed
                video.error_message = str(exc)[:2000]
                db.commit()
    finally:
        db.close()


def reap_stuck_jobs(db: Session, *, older_than: timedelta | None = None) -> int:
    """Mark stuck video jobs as `failed` so they don't poll forever.

    A `Video` can be left in `pending`/`downloading`/`processing` forever if
    the worker process that owned its `process_video_job` background task
    crashes or is restarted mid-job (nothing else ever transitions it out of
    that state), or if a network/subprocess call inside the pipeline hangs
    without ever raising.

    With `older_than=None`, every row in an active status is reaped
    unconditionally — used once at startup, since a fresh process can't
    possibly have a genuinely in-flight job yet: anything active in the DB
    at boot is necessarily orphaned from a previous process. With
    `older_than` set, only rows whose `updated_at` is older than that are
    reaped — used by the periodic watchdog to catch jobs hung *within* an
    otherwise-healthy running process, without touching jobs that are still
    legitimately in progress.

    Returns the number of rows reaped.
    """
    query = db.query(Video).filter(Video.status.in_(_ACTIVE_STATUSES))

    if older_than is not None:
        cutoff = datetime.now(UTC) - older_than
        query = query.filter(Video.updated_at < cutoff)

    stuck_jobs = query.all()
    for video in stuck_jobs:
        logger.warning(
            "Reaping stuck video job id=%s status=%s updated_at=%s",
            video.id,
            video.status,
            video.updated_at,
        )
        video.status = VideoStatus.failed
        video.error_message = "Job timed out or was interrupted (server restart or a hung step)."
    db.commit()

    return len(stuck_jobs)


def cleanup_expired_video_files(db: Session, *, older_than: timedelta) -> int:
    """Delete on-disk files for old, terminal-status videos to bound storage growth.

    Without this, `backend/storage/` grows without bound: every completed
    job's output file is kept forever with no retention policy. This only
    ever deletes files, never the `Video` row itself — history stays intact
    and `GET /videos/{id}/download` already 404s gracefully via
    `get_download_path` once the underlying file is gone.

    Only rows with `output_url` still set are considered, so a row already
    cleaned up (or one whose output was never persisted, e.g. a `failed`
    job) isn't re-processed on every sweep — `output_url` doubles as the
    "has a file worth cleaning up" marker.

    Returns the number of videos cleaned up.
    """
    cutoff = datetime.now(UTC) - older_than
    expired = (
        db.query(Video)
        .filter(
            Video.status.in_((VideoStatus.completed, VideoStatus.failed)),
            Video.output_url.is_not(None),
            Video.created_at < cutoff,
        )
        .all()
    )

    if not expired:
        return 0

    storage = get_storage_backend()
    for video in expired:
        logger.info("Cleaning up expired storage for video id=%s (created_at=%s)", video.id, video.created_at)
        storage.delete(_source_key(video.id))
        storage.delete(_output_key(video.id))
        video.output_url = None
    db.commit()

    return len(expired)


def list_videos(db: Session, user_id: int, params: VideoListParams) -> list[Video]:
    """List the requesting user's videos, optionally filtered by status/search."""
    query = db.query(Video).filter(Video.user_id == user_id)

    if params.status is not None:
        query = query.filter(Video.status == params.status)

    if params.search:
        like = f"%{params.search}%"
        query = query.filter(Video.source_title.ilike(like))

    return (
        query.order_by(Video.created_at.desc())
        .offset(params.skip)
        .limit(params.limit)
        .all()
    )


def get_video_for_user(db: Session, user_id: int, video_id: int) -> Video:
    """Fetch a video by id, scoped to `user_id`. Raises `NotFoundError` otherwise."""
    video = db.query(Video).filter(Video.id == video_id, Video.user_id == user_id).first()
    if video is None:
        raise NotFoundError("Video not found")
    return video


def get_download_path(video: Video) -> Path:
    """Resolve the local filesystem path of a completed video's output file."""
    if video.status != VideoStatus.completed:
        raise ConflictError("Video is not ready for download")

    storage = get_storage_backend()
    path = storage.resolve_path(_output_key(video.id))
    if not path.exists():
        raise NotFoundError("Output file not found")
    return path


def delete_video(db: Session, video: Video) -> None:
    """Delete a video's DB row and its stored source/output files.

    Refuses to delete a job that's still active (`pending`/`downloading`/
    `processing`). Without this, deleting mid-flight races the background
    `process_video_job` task: the row disappears out from under it, but it
    keeps writing to `storage` regardless, leaving orphaned source/output
    files on disk with nothing left to reference or clean them up.

    This is safe to check against the already-loaded `video` object (no
    extra re-fetch/lock needed) because the status machine only moves
    forward — active statuses eventually become `completed`/`failed`, and
    a row never transitions back out of a terminal status. So a `video`
    read as active might complete moments later (the caller just has to
    retry), but a `video` read as terminal is guaranteed to stay terminal,
    with the background task already done touching its row and files.
    """
    if video.status in _ACTIVE_STATUSES:
        raise ConflictError(
            "Cannot delete a video while it's still being processed. "
            "Wait for it to finish (or fail) and try again."
        )

    storage = get_storage_backend()
    storage.delete(_source_key(video.id))
    storage.delete(_output_key(video.id))
    db.delete(video)
    db.commit()
    logger.info("Deleted video id=%s", video.id)

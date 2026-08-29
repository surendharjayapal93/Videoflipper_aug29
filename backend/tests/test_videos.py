"""Tests for `/api/v1/videos/*` and the underlying `video_service` orchestration.

`youtube_downloader.download_video` and `video_processing.flip_video` are
always mocked here -- tests must never hit real YouTube or shell out to a
real `ffmpeg` binary. `validate_youtube_url` is pure string parsing (no
network) and is exercised for real.

`get_storage_backend` is also patched (autouse) to a `LocalStorageBackend`
rooted at a per-test `tmp_path` rather than the real `backend/storage/`
directory, so tests never leave files behind in the repo.
"""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.exceptions import ValidationError
from app.models.video import FlipDirection, Video, VideoStatus
from app.services import video_service
from app.services.storage import LocalStorageBackend
from app.services.youtube_downloader import validate_youtube_url

VALID_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture(autouse=True)
def patch_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect `video_service.get_storage_backend` to a tmp-dir-backed store."""
    backend = LocalStorageBackend(tmp_path / "storage")
    monkeypatch.setattr(video_service, "get_storage_backend", lambda: backend)


def _fake_download_success(youtube_url: str, dest_path: Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(b"fake source video bytes")
    return {"title": "Mock Video Title", "duration_seconds": 42.0, "file_size_bytes": 24}


def _fake_flip_success(input_path: Path, output_path: Path, direction: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"fake flipped video bytes")


def _fake_download_failure(youtube_url: str, dest_path: Path):
    raise RuntimeError("simulated downloader failure")


def _create_video_row(
    db: Session,
    user_id: int,
    *,
    status: VideoStatus = VideoStatus.pending,
    source_title: str | None = None,
    flip_direction: FlipDirection = FlipDirection.horizontal,
    file_size_bytes: int | None = None,
) -> Video:
    video = Video(
        user_id=user_id,
        youtube_url=VALID_URL,
        youtube_video_id="dQw4w9WgXcQ",
        source_title=source_title,
        flip_direction=flip_direction,
        status=status,
        file_size_bytes=file_size_bytes,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


# --- validate_youtube_url (pure, no mocking) ---------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
    ],
)
def test_validate_youtube_url_accepts_valid_urls(url: str) -> None:
    assert validate_youtube_url(url) == "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        "https://vimeo.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/playlist?list=PLabc",
        "ftp://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "not a url at all",
        "",
        "https://youtu.be/short",
    ],
)
def test_validate_youtube_url_rejects_invalid_urls(url: str) -> None:
    with pytest.raises(ValidationError):
        validate_youtube_url(url)


# --- create_video_job / process_video_job orchestration ---------------------


def test_create_video_reaches_completed_status(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(video_service, "download_video", _fake_download_success)
    monkeypatch.setattr(video_service.video_processing, "flip_video", _fake_flip_success)

    create_response = client.post(
        "/api/v1/videos",
        json={"youtube_url": VALID_URL, "flip_direction": "horizontal"},
        headers=auth_headers,
    )
    assert create_response.status_code == 202
    video_id = create_response.json()["id"]

    # TestClient blocks until FastAPI's BackgroundTasks (our mocked pipeline)
    # has finished running, so the job is already done by the time we get here.
    get_response = client.get(f"/api/v1/videos/{video_id}", headers=auth_headers)
    body = get_response.json()

    assert body["status"] == "completed"
    assert body["source_title"] == "Mock Video Title"
    assert body["duration_seconds"] == 42.0
    assert body["file_size_bytes"] == len(b"fake flipped video bytes")
    assert body["error_message"] is None


def test_create_video_marks_failed_on_downloader_exception(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(video_service, "download_video", _fake_download_failure)
    monkeypatch.setattr(video_service.video_processing, "flip_video", _fake_flip_success)

    create_response = client.post(
        "/api/v1/videos",
        json={"youtube_url": VALID_URL, "flip_direction": "vertical"},
        headers=auth_headers,
    )
    video_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/videos/{video_id}", headers=auth_headers)
    body = get_response.json()

    assert body["status"] == "failed"
    assert "simulated downloader failure" in body["error_message"]


def test_create_video_rejects_non_youtube_url(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/videos",
        json={"youtube_url": "https://vimeo.com/12345", "flip_direction": "horizontal"},
        headers=auth_headers,
    )

    assert response.status_code == 422


# --- list endpoint filters ----------------------------------------------------


def test_list_videos_filters_by_status(
    client: TestClient, auth_headers: dict[str, str], registered_user, db: Session
) -> None:
    _create_video_row(db, registered_user.id, status=VideoStatus.completed, source_title="Done one")
    _create_video_row(db, registered_user.id, status=VideoStatus.failed, source_title="Broken one")

    response = client.get("/api/v1/videos", params={"status": "completed"}, headers=auth_headers)

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["status"] == "completed"


def test_list_videos_filters_by_search(
    client: TestClient, auth_headers: dict[str, str], registered_user, db: Session
) -> None:
    _create_video_row(db, registered_user.id, source_title="Funny cat video")
    _create_video_row(db, registered_user.id, source_title="Serious lecture")

    response = client.get("/api/v1/videos", params={"search": "cat"}, headers=auth_headers)

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["source_title"] == "Funny cat video"


# --- ownership isolation -------------------------------------------------------


def test_get_video_not_owned_returns_404(
    client: TestClient, auth_headers: dict[str, str], create_user, db: Session
) -> None:
    other_user, _ = create_user(email="other@example.com")
    other_video = _create_video_row(db, other_user.id)

    response = client.get(f"/api/v1/videos/{other_video.id}", headers=auth_headers)

    assert response.status_code == 404


def test_list_videos_only_returns_own_videos(
    client: TestClient, auth_headers: dict[str, str], registered_user, create_user, db: Session
) -> None:
    _create_video_row(db, registered_user.id, source_title="Mine")
    other_user, _ = create_user(email="other2@example.com")
    _create_video_row(db, other_user.id, source_title="Not mine")

    response = client.get("/api/v1/videos", headers=auth_headers)

    assert response.status_code == 200
    titles = [v["source_title"] for v in response.json()]
    assert titles == ["Mine"]


# --- download endpoint ---------------------------------------------------------


def test_download_video_conflict_when_not_completed(
    client: TestClient, auth_headers: dict[str, str], registered_user, db: Session
) -> None:
    video = _create_video_row(db, registered_user.id, status=VideoStatus.processing)

    response = client.get(f"/api/v1/videos/{video.id}/download", headers=auth_headers)

    assert response.status_code == 409


def test_download_video_success(
    client: TestClient,
    auth_headers: dict[str, str],
    registered_user,
    db: Session,
    tmp_path: Path,
) -> None:
    video = _create_video_row(db, registered_user.id, status=VideoStatus.completed)

    storage = LocalStorageBackend(tmp_path / "storage")
    output_path = storage.resolve_path(f"{video.id}/output.mp4")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"the flipped output")

    response = client.get(f"/api/v1/videos/{video.id}/download", headers=auth_headers)

    assert response.status_code == 200
    assert response.content == b"the flipped output"


def test_download_video_not_owned_returns_404(
    client: TestClient, auth_headers: dict[str, str], create_user, db: Session
) -> None:
    other_user, _ = create_user(email="other3@example.com")
    other_video = _create_video_row(db, other_user.id, status=VideoStatus.completed)

    response = client.get(f"/api/v1/videos/{other_video.id}/download", headers=auth_headers)

    assert response.status_code == 404


# --- delete endpoint -------------------------------------------------------------


def test_delete_video_removes_db_row(
    client: TestClient, auth_headers: dict[str, str], registered_user, db: Session
) -> None:
    video = _create_video_row(db, registered_user.id, status=VideoStatus.completed)
    video_id = video.id

    response = client.delete(f"/api/v1/videos/{video_id}", headers=auth_headers)

    assert response.status_code == 204
    assert db.query(Video).filter(Video.id == video_id).first() is None


def test_delete_video_not_owned_returns_404(
    client: TestClient, auth_headers: dict[str, str], create_user, db: Session
) -> None:
    other_user, _ = create_user(email="other4@example.com")
    other_video = _create_video_row(db, other_user.id)

    response = client.delete(f"/api/v1/videos/{other_video.id}", headers=auth_headers)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "active_status",
    [VideoStatus.pending, VideoStatus.downloading, VideoStatus.processing],
)
def test_delete_video_conflict_while_active(
    client: TestClient,
    auth_headers: dict[str, str],
    registered_user,
    db: Session,
    active_status: VideoStatus,
) -> None:
    """Deleting a job that's still being processed must be rejected, not
    race the background `process_video_job` task and orphan its files."""
    video = _create_video_row(db, registered_user.id, status=active_status)
    video_id = video.id

    response = client.delete(f"/api/v1/videos/{video_id}", headers=auth_headers)

    assert response.status_code == 409
    # The row must still exist -- the delete was refused, not partially applied.
    assert db.query(Video).filter(Video.id == video_id).first() is not None


def test_delete_video_allowed_after_failed(
    client: TestClient, auth_headers: dict[str, str], registered_user, db: Session
) -> None:
    """A terminal `failed` status (e.g. reaped by the watchdog) is deletable."""
    video = _create_video_row(db, registered_user.id, status=VideoStatus.failed)
    video_id = video.id

    response = client.delete(f"/api/v1/videos/{video_id}", headers=auth_headers)

    assert response.status_code == 204
    assert db.query(Video).filter(Video.id == video_id).first() is None


# --- reap_stuck_jobs (watchdog) --------------------------------------------------


def test_reap_stuck_jobs_marks_all_active_when_no_age_threshold(
    db: Session, registered_user
) -> None:
    """`older_than=None` is the startup sweep: reap every active job
    unconditionally, since a fresh process can't have a real one in flight."""
    video = _create_video_row(db, registered_user.id, status=VideoStatus.processing)

    reaped = video_service.reap_stuck_jobs(db)

    assert reaped == 1
    db.refresh(video)
    assert video.status == VideoStatus.failed
    assert video.error_message
    assert "interrupted" in video.error_message or "timed out" in video.error_message


def test_reap_stuck_jobs_ignores_terminal_statuses(db: Session, registered_user) -> None:
    completed = _create_video_row(db, registered_user.id, status=VideoStatus.completed)
    failed = _create_video_row(db, registered_user.id, status=VideoStatus.failed)

    reaped = video_service.reap_stuck_jobs(db)

    assert reaped == 0
    db.refresh(completed)
    db.refresh(failed)
    assert completed.status == VideoStatus.completed
    assert failed.status == VideoStatus.failed


def test_reap_stuck_jobs_with_age_threshold_only_reaps_stale_rows(
    db: Session, registered_user
) -> None:
    """The periodic watchdog only reaps jobs stale beyond the threshold,
    leaving genuinely-in-progress jobs alone."""
    stale = _create_video_row(db, registered_user.id, status=VideoStatus.downloading)
    fresh = _create_video_row(db, registered_user.id, status=VideoStatus.processing)

    # Backdate `stale`'s updated_at directly via a bulk UPDATE, which bypasses
    # the mapped column's onupdate=func.now() default (only applied by the
    # ORM's own flush of a modified instance, not a Query.update() call).
    old_time = datetime.now(UTC) - timedelta(minutes=30)
    db.query(Video).filter(Video.id == stale.id).update({"updated_at": old_time})
    db.commit()

    reaped = video_service.reap_stuck_jobs(db, older_than=timedelta(minutes=20))

    assert reaped == 1
    db.refresh(stale)
    db.refresh(fresh)
    assert stale.status == VideoStatus.failed
    assert fresh.status == VideoStatus.processing

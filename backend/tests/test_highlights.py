"""Tests for `/api/v1/highlights/*` and the underlying `highlight_service` orchestration.

`youtube_downloader.download_video` and every ffmpeg/ffprobe-backed
function in `highlight_extraction` are always mocked here -- tests must
never hit real YouTube or shell out to real ffmpeg/ffprobe binaries.

`get_storage_backend` is also patched (autouse) to a `LocalStorageBackend`
rooted at a per-test `tmp_path` rather than the real `backend/storage/`
directory, so tests never leave files behind in the repo.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.highlight import Highlight, HighlightStatus
from app.services import highlight_service
from app.services.highlight_extraction import Segment
from app.services.storage import LocalStorageBackend

VALID_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture(autouse=True)
def patch_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Redirect `highlight_service.get_storage_backend` to a tmp-dir-backed store."""
    backend = LocalStorageBackend(tmp_path / "storage")
    monkeypatch.setattr(highlight_service, "get_storage_backend", lambda: backend)


def _fake_download_success(youtube_url: str, dest_path: Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(b"fake source video bytes")
    return {"title": "Mock Video Title", "duration_seconds": 120.0, "file_size_bytes": 24}


def _fake_download_failure(youtube_url: str, dest_path: Path):
    raise RuntimeError("simulated downloader failure")


def _fake_probe_duration(input_path: Path) -> float:
    return 120.0


def _fake_detect_active_segments(input_path: Path, total_duration: float) -> list[Segment]:
    return [Segment(0.0, 60.0)]


def _fake_select_highlight_segments(active_segments, total_duration, target_duration=60.0):
    return [Segment(0.0, 60.0)]


def _fake_render_success(input_path: Path, segments, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"fake highlight reel bytes")


def _patch_pipeline_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(highlight_service, "download_video", _fake_download_success)
    monkeypatch.setattr(highlight_service.highlight_extraction, "probe_duration_seconds", _fake_probe_duration)
    monkeypatch.setattr(
        highlight_service.highlight_extraction, "detect_active_segments", _fake_detect_active_segments
    )
    monkeypatch.setattr(
        highlight_service.highlight_extraction, "select_highlight_segments", _fake_select_highlight_segments
    )
    monkeypatch.setattr(highlight_service.highlight_extraction, "render_highlight_reel", _fake_render_success)


def _create_highlight_row(
    db: Session, user_id: int, *, status: HighlightStatus = HighlightStatus.pending
) -> Highlight:
    highlight = Highlight(
        user_id=user_id,
        youtube_url=VALID_URL,
        youtube_video_id="dQw4w9WgXcQ",
        status=status,
    )
    db.add(highlight)
    db.commit()
    db.refresh(highlight)
    return highlight


# --- create_highlight_job / process_highlight_job orchestration -----------------


def test_create_highlight_reaches_completed_status(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_pipeline_success(monkeypatch)

    create_response = client.post("/api/v1/highlights", json={"youtube_url": VALID_URL}, headers=auth_headers)
    assert create_response.status_code == 202
    highlight_id = create_response.json()["id"]

    # TestClient blocks until FastAPI's BackgroundTasks (our mocked pipeline)
    # has finished running, so the job is already done by the time we get here.
    get_response = client.get(f"/api/v1/highlights/{highlight_id}", headers=auth_headers)
    body = get_response.json()

    assert body["status"] == "completed"
    assert body["source_title"] == "Mock Video Title"
    assert body["source_duration_seconds"] == 120.0
    assert body["highlight_duration_seconds"] == 60.0
    assert body["file_size_bytes"] == len(b"fake highlight reel bytes")
    assert body["error_message"] is None


def test_create_highlight_marks_failed_on_downloader_exception(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(highlight_service, "download_video", _fake_download_failure)

    create_response = client.post("/api/v1/highlights", json={"youtube_url": VALID_URL}, headers=auth_headers)
    highlight_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/highlights/{highlight_id}", headers=auth_headers)
    body = get_response.json()

    assert body["status"] == "failed"
    assert "simulated downloader failure" in body["error_message"]


def test_create_highlight_marks_failed_on_render_exception(
    client: TestClient, auth_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_render_failure(input_path: Path, segments, output_path: Path) -> None:
        raise RuntimeError("simulated ffmpeg render failure")

    monkeypatch.setattr(highlight_service, "download_video", _fake_download_success)
    monkeypatch.setattr(highlight_service.highlight_extraction, "probe_duration_seconds", _fake_probe_duration)
    monkeypatch.setattr(
        highlight_service.highlight_extraction, "detect_active_segments", _fake_detect_active_segments
    )
    monkeypatch.setattr(
        highlight_service.highlight_extraction, "select_highlight_segments", _fake_select_highlight_segments
    )
    monkeypatch.setattr(highlight_service.highlight_extraction, "render_highlight_reel", _fake_render_failure)

    create_response = client.post("/api/v1/highlights", json={"youtube_url": VALID_URL}, headers=auth_headers)
    highlight_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/highlights/{highlight_id}", headers=auth_headers)
    body = get_response.json()

    assert body["status"] == "failed"
    assert "simulated ffmpeg render failure" in body["error_message"]


def test_create_highlight_rejects_non_youtube_url(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post("/api/v1/highlights", json={"youtube_url": "https://vimeo.com/12345"}, headers=auth_headers)

    assert response.status_code == 422


# --- ownership isolation -------------------------------------------------------


def test_get_highlight_not_owned_returns_404(
    client: TestClient, auth_headers: dict[str, str], create_user, db: Session
) -> None:
    other_user, _ = create_user(email="other-highlight@example.com")
    other_highlight = _create_highlight_row(db, other_user.id)

    response = client.get(f"/api/v1/highlights/{other_highlight.id}", headers=auth_headers)

    assert response.status_code == 404


# --- download endpoint ---------------------------------------------------------


def test_download_highlight_conflict_when_not_completed(
    client: TestClient, auth_headers: dict[str, str], registered_user, db: Session
) -> None:
    highlight = _create_highlight_row(db, registered_user.id, status=HighlightStatus.rendering)

    response = client.get(f"/api/v1/highlights/{highlight.id}/download", headers=auth_headers)

    assert response.status_code == 409


def test_download_highlight_success(
    client: TestClient,
    auth_headers: dict[str, str],
    registered_user,
    db: Session,
    tmp_path: Path,
) -> None:
    highlight = _create_highlight_row(db, registered_user.id, status=HighlightStatus.completed)

    storage = LocalStorageBackend(tmp_path / "storage")
    output_path = storage.resolve_path(f"highlights/{highlight.id}/output.mp4")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"the highlight reel bytes")

    response = client.get(f"/api/v1/highlights/{highlight.id}/download", headers=auth_headers)

    assert response.status_code == 200
    assert response.content == b"the highlight reel bytes"


def test_download_highlight_not_owned_returns_404(
    client: TestClient, auth_headers: dict[str, str], create_user, db: Session
) -> None:
    other_user, _ = create_user(email="other-highlight2@example.com")
    other_highlight = _create_highlight_row(db, other_user.id, status=HighlightStatus.completed)

    response = client.get(f"/api/v1/highlights/{other_highlight.id}/download", headers=auth_headers)

    assert response.status_code == 404

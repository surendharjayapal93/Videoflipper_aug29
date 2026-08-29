"""Tests for `GET /api/v1/dashboard/stats`."""

from __future__ import annotations

from datetime import datetime, timedelta, UTC

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.video import FlipDirection, Video, VideoStatus

VALID_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def _make_video(
    db: Session,
    user_id: int,
    status: VideoStatus,
    *,
    source_title: str | None = None,
    file_size_bytes: int | None = None,
    created_at: datetime | None = None,
) -> Video:
    video = Video(
        user_id=user_id,
        youtube_url=VALID_URL,
        youtube_video_id="dQw4w9WgXcQ",
        source_title=source_title,
        flip_direction=FlipDirection.horizontal,
        status=status,
        file_size_bytes=file_size_bytes,
    )
    if created_at is not None:
        # `created_at` normally comes from the DB's `server_default=func.now()`,
        # which on SQLite only has 1-second resolution -- rows inserted back
        # to back in the same test can tie. Setting it explicitly lets tests
        # that assert on ordering stay deterministic.
        video.created_at = created_at
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def test_dashboard_stats_aggregate_mixed_statuses(
    client: TestClient, auth_headers: dict[str, str], registered_user, db: Session
) -> None:
    _make_video(db, registered_user.id, VideoStatus.completed, source_title="a", file_size_bytes=100)
    _make_video(db, registered_user.id, VideoStatus.completed, source_title="b", file_size_bytes=250)
    _make_video(db, registered_user.id, VideoStatus.failed, source_title="c")
    _make_video(db, registered_user.id, VideoStatus.pending, source_title="d")
    _make_video(db, registered_user.id, VideoStatus.downloading, source_title="e")
    _make_video(db, registered_user.id, VideoStatus.processing, source_title="f")

    response = client.get("/api/v1/dashboard/stats", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_videos"] == 6
    assert body["completed_videos"] == 2
    assert body["failed_videos"] == 1
    assert body["processing_videos"] == 3  # pending + downloading + processing
    assert body["total_storage_bytes"] == 350
    # completed + failed + processing must always account for every video.
    assert (
        body["completed_videos"] + body["failed_videos"] + body["processing_videos"]
        == body["total_videos"]
    )


def test_dashboard_stats_recent_activity_limited_and_ordered(
    client: TestClient, auth_headers: dict[str, str], registered_user, db: Session
) -> None:
    base_time = datetime.now(UTC)
    for i in range(7):
        _make_video(
            db,
            registered_user.id,
            VideoStatus.completed,
            source_title=f"video-{i}",
            created_at=base_time + timedelta(seconds=i),
        )

    response = client.get("/api/v1/dashboard/stats", headers=auth_headers)

    body = response.json()
    assert body["total_videos"] == 7
    assert len(body["recent_activity"]) == 5
    # Most recently created first.
    assert body["recent_activity"][0]["source_title"] == "video-6"


def test_dashboard_stats_empty_for_new_user(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/dashboard/stats", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_videos"] == 0
    assert body["completed_videos"] == 0
    assert body["failed_videos"] == 0
    assert body["processing_videos"] == 0
    assert body["total_storage_bytes"] == 0
    assert body["recent_activity"] == []


def test_dashboard_stats_scoped_to_requesting_user_only(
    client: TestClient, auth_headers: dict[str, str], registered_user, create_user, db: Session
) -> None:
    _make_video(db, registered_user.id, VideoStatus.completed, source_title="mine", file_size_bytes=10)

    other_user, _ = create_user(email="dashboard-other@example.com")
    # Seed a second user's videos with statuses/sizes that would change the
    # aggregates if they leaked into the requesting user's stats.
    _make_video(db, other_user.id, VideoStatus.completed, source_title="not mine", file_size_bytes=99999)
    _make_video(db, other_user.id, VideoStatus.failed, source_title="also not mine")

    response = client.get("/api/v1/dashboard/stats", headers=auth_headers)

    body = response.json()
    assert body["total_videos"] == 1
    assert body["completed_videos"] == 1
    assert body["failed_videos"] == 0
    assert body["total_storage_bytes"] == 10
    assert [v["source_title"] for v in body["recent_activity"]] == ["mine"]


def test_dashboard_stats_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard/stats")

    assert response.status_code == 401

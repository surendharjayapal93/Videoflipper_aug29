"""YouTube URL validation and download via yt-dlp.

Security note: `validate_youtube_url` MUST be called (and must pass)
before any URL is ever handed to yt-dlp. yt-dlp will happily fetch from
whatever host/URL it is given, and yt-dlp extractors have historically
had bugs; restricting the accepted hosts to a strict YouTube allowlist
before invoking it prevents the download pipeline from being used as an
open SSRF-style fetcher for arbitrary internal or external URLs.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TypedDict
from urllib.parse import parse_qs, urlparse

import yt_dlp

from app.exceptions import ValidationError


class VideoMetadata(TypedDict):
    """Metadata returned by `download_video` for a successfully fetched video."""

    title: str | None
    duration_seconds: float | None
    file_size_bytes: int

logger = logging.getLogger(__name__)

# Only these exact hosts are accepted. Subdomains/typosquats (e.g.
# "youtube.com.evil.example") are rejected by exact-match comparison below.
_ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

MAX_DURATION_SECONDS = 10 * 60  # 10 minutes
MAX_FILESIZE_BYTES = 200 * 1024 * 1024  # 200 MB


def validate_youtube_url(url: str) -> str:
    """Validate that `url` is a well-formed, public YouTube video URL.

    Returns the extracted 11-character YouTube video ID on success.
    Raises `ValidationError` for anything that isn't a plain, public
    `youtube.com` / `youtu.be` watch URL (wrong host, playlist-only link,
    malformed ID, etc.).
    """
    url = url.strip()
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise ValidationError("Malformed URL") from exc

    if parsed.scheme not in {"http", "https"}:
        raise ValidationError("URL must use http or https")

    host = (parsed.hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise ValidationError("Only youtube.com / youtu.be URLs are accepted")

    video_id: str | None = None

    if host == "youtu.be":
        # https://youtu.be/<id>
        video_id = parsed.path.lstrip("/").split("/")[0]
    else:
        if parsed.path == "/watch":
            query = parse_qs(parsed.query)
            values = query.get("v")
            video_id = values[0] if values else None
        elif parsed.path.startswith("/shorts/"):
            video_id = parsed.path.removeprefix("/shorts/").split("/")[0]
        elif parsed.path.startswith("/embed/"):
            video_id = parsed.path.removeprefix("/embed/").split("/")[0]

    if not video_id or not _VIDEO_ID_RE.match(video_id):
        raise ValidationError("Could not extract a valid YouTube video ID from URL")

    return video_id


def download_video(youtube_url: str, dest_path: Path) -> VideoMetadata:
    """Download `youtube_url` to `dest_path` using yt-dlp.

    `youtube_url` MUST already have passed `validate_youtube_url`. Enforces
    `MAX_DURATION_SECONDS` and `MAX_FILESIZE_BYTES`: metadata is checked
    before the download starts (cheap rejection), and yt-dlp's own
    `max_filesize` guard is applied as a hard stop during download.

    Returns a dict with `title`, `duration_seconds`, and `file_size_bytes`.
    Raises `ValidationError` if the video exceeds the configured limits or
    metadata cannot be fetched.
    """
    # Re-validate defensively: this function must never be reachable with a
    # URL that hasn't been through the host/format allowlist.
    validate_youtube_url(youtube_url)

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(dest_path),
        "max_filesize": MAX_FILESIZE_BYTES,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "logger": logger,
        "merge_output_format": "mp4",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            if info is None:
                raise ValidationError("Could not fetch video metadata")

            duration = info.get("duration")
            if duration is not None and duration > MAX_DURATION_SECONDS:
                raise ValidationError(
                    f"Video duration ({duration}s) exceeds the maximum allowed "
                    f"({MAX_DURATION_SECONDS}s)"
                )

            filesize = info.get("filesize") or info.get("filesize_approx")
            if filesize is not None and filesize > MAX_FILESIZE_BYTES:
                raise ValidationError(
                    f"Video file size ({filesize} bytes) exceeds the maximum "
                    f"allowed ({MAX_FILESIZE_BYTES} bytes)"
                )

            title = info.get("title")

            logger.info("Downloading YouTube video id=%s to %s", info.get("id"), dest_path)
            ydl.download([youtube_url])

    except yt_dlp.utils.DownloadError as exc:
        logger.error("yt-dlp download failed for %s: %s", youtube_url, exc)
        raise ValidationError(f"Failed to download video: {exc}") from exc

    if not dest_path.exists():
        # yt-dlp may have written a different extension via outtmpl/merge;
        # look for the actual produced file.
        candidates = list(dest_path.parent.glob(f"{dest_path.stem}.*"))
        if not candidates:
            raise ValidationError("Download completed but output file was not found")
        actual_path = candidates[0]
        actual_path.rename(dest_path)

    file_size_bytes = dest_path.stat().st_size
    if file_size_bytes > MAX_FILESIZE_BYTES:
        dest_path.unlink(missing_ok=True)
        raise ValidationError(
            f"Downloaded file size ({file_size_bytes} bytes) exceeds the maximum "
            f"allowed ({MAX_FILESIZE_BYTES} bytes)"
        )

    return {
        "title": title,
        "duration_seconds": duration,
        "file_size_bytes": file_size_bytes,
    }

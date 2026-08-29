"""Storage abstraction for video source/output files.

`StorageBackend` is the swap point: this phase ships a single concrete
`LocalStorageBackend` that persists files under `backend/storage/` on
disk. A future phase can add an `S3StorageBackend` (using
`settings.STORAGE_BUCKET` / `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY`)
that implements the same protocol, and callers (video_service.py) would
not need to change at all.

Keys are opaque strings chosen by the caller (e.g.
`"{video_id}/source.mp4"`); each backend maps a key to wherever it
actually keeps the bytes.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class StorageBackend(Protocol):
    """Interface for persisting and retrieving video files by key."""

    def save(self, key: str, source_path: Path) -> str:
        """Persist the file at `source_path` under `key`.

        Returns a backend-specific reference (path or URL) that can later
        be passed to `resolve_path` / `delete`.
        """
        ...

    def resolve_path(self, key: str) -> Path:
        """Return a local filesystem path that can be read/streamed for `key`."""
        ...

    def delete(self, key: str) -> None:
        """Remove the file stored under `key`, if it exists."""
        ...


class LocalStorageBackend:
    """Filesystem-backed `StorageBackend` storing files under a root directory."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        # Reject path traversal / absolute keys — keys must stay inside root.
        candidate = (self._root / key).resolve()
        root_resolved = self._root.resolve()
        if root_resolved not in candidate.parents and candidate != root_resolved:
            raise ValueError(f"Invalid storage key: {key!r}")
        return candidate

    def save(self, key: str, source_path: Path) -> str:
        dest = self._full_path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve() != dest.resolve():
            shutil.copy2(source_path, dest)
        logger.info("Stored file under key=%s at %s", key, dest)
        return str(dest)

    def resolve_path(self, key: str) -> Path:
        return self._full_path(key)

    def delete(self, key: str) -> None:
        path = self._full_path(key)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Failed to delete stored file for key=%s at %s", key, path, exc_info=True)


def get_storage_backend() -> StorageBackend:
    """Return the active `StorageBackend`.

    This phase always returns a `LocalStorageBackend` rooted at
    `backend/storage/`. Swapping to S3-compatible storage later means
    reading `get_settings().STORAGE_BUCKET` / `STORAGE_ACCESS_KEY` /
    `STORAGE_SECRET_KEY` here and returning an `S3StorageBackend` instead
    — no other module needs to change.
    """
    storage_root = Path(__file__).resolve().parent.parent.parent / "storage"
    return LocalStorageBackend(storage_root)

"""Minimal in-memory rate limiter for auth endpoints.

Chosen over `slowapi` to avoid adding a new dependency for a single-process
dev/small-deployment app. This is a fixed-window counter keyed by client IP
+ route, stored in a plain dict.

Known limitations (acceptable for this stage, revisit before scaling out):
- State is per-process: it resets on restart and is NOT shared across
  multiple uvicorn/gunicorn workers or hosts. If the app is later run
  with multiple workers, swap this for a shared store (e.g. Redis-backed
  `slowapi` limiter) so limits are enforced consistently.
- Client IP is taken from `request.client.host`; if the app sits behind a
  proxy/load balancer, configure trusted proxy headers (e.g.
  `X-Forwarded-For`) before relying on this in production.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# key -> list of request timestamps (seconds) within the current window
_hits: dict[str, list[float]] = defaultdict(list)


def rate_limit(max_requests: int, window_seconds: int):
    """Build a FastAPI dependency limiting a route to `max_requests` per `window_seconds` per client IP."""

    async def _dependency(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        key = f"{request.url.path}:{client_host}"

        now = time.monotonic()
        window_start = now - window_seconds

        timestamps = _hits[key]
        # Drop timestamps outside the current window.
        timestamps[:] = [t for t in timestamps if t > window_start]

        if len(timestamps) >= max_requests:
            logger.warning("Rate limit exceeded for %s", key)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        timestamps.append(now)

    return _dependency

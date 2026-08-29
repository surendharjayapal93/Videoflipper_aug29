"""FastAPI application entrypoint for VideoFlipper.

This phase wires up the app instance, CORS, and global exception
handling only. Routers are added in a later phase.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import SessionLocal
from app.exceptions import register_exception_handlers
from app.routers import auth, dashboard, highlights, videos
from app.services.video_service import cleanup_expired_video_files, reap_stuck_jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


async def _maintenance_loop() -> None:
    """Periodic background upkeep: reap stuck jobs and clean up old storage.

    Two independent concerns share one timer since both are cheap, DB-bound
    sweeps with no reason to run on separate schedules:

    - Reaping guards against a download/flip step hanging (no exception
      ever raised) within an otherwise-healthy running process. The
      startup sweep in `lifespan` handles the "process crashed/restarted
      mid-job" case; this loop handles the "process is fine but a job is
      hung" case.
    - Cleanup deletes on-disk output files for old completed/failed jobs
      so `backend/storage/` doesn't grow without bound; the `Video` row
      (and its history) is kept either way.
    """
    interval = settings.WATCHDOG_INTERVAL_SECONDS
    stale_after = timedelta(minutes=settings.STUCK_JOB_TIMEOUT_MINUTES)
    retention = timedelta(days=settings.STORAGE_RETENTION_DAYS)
    while True:
        await asyncio.sleep(interval)
        db = SessionLocal()
        try:
            reaped = await asyncio.to_thread(reap_stuck_jobs, db, older_than=stale_after)
            if reaped:
                logger.warning("Watchdog reaped %d stuck video job(s)", reaped)

            cleaned = await asyncio.to_thread(cleanup_expired_video_files, db, older_than=retention)
            if cleaned:
                logger.info("Storage cleanup removed files for %d expired video(s)", cleaned)
        except Exception:
            logger.exception("Maintenance sweep failed")
        finally:
            db.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown hooks."""
    logger.info("%s starting up", settings.APP_NAME)

    # Any video still in an active status at boot is necessarily orphaned
    # from a previous process (this one hasn't scheduled any jobs yet).
    db = SessionLocal()
    try:
        reaped = reap_stuck_jobs(db)
        if reaped:
            logger.warning("Startup sweep reaped %d orphaned video job(s)", reaped)
    finally:
        db.close()

    maintenance_task = asyncio.create_task(_maintenance_loop())
    try:
        yield
    finally:
        maintenance_task.cancel()
        try:
            await maintenance_task
        except asyncio.CancelledError:
            pass
        logger.info("%s shutting down", settings.APP_NAME)


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # e.g. Vite dev server at http://localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(videos.router, prefix="/api/v1")
app.include_router(highlights.router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness/readiness check endpoint."""
    return {"status": "ok"}

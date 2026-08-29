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
from app.routers import auth, dashboard, videos
from app.services.video_service import reap_stuck_jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


async def _watchdog_loop() -> None:
    """Periodically fail any video job stuck too long in an active status.

    Guards against a download/flip step hanging (no exception ever raised)
    within an otherwise-healthy running process. The startup sweep in
    `lifespan` handles the "process crashed/restarted mid-job" case; this
    loop handles the "process is fine but a job is hung" case.
    """
    interval = settings.WATCHDOG_INTERVAL_SECONDS
    stale_after = timedelta(minutes=settings.STUCK_JOB_TIMEOUT_MINUTES)
    while True:
        await asyncio.sleep(interval)
        db = SessionLocal()
        try:
            reaped = await asyncio.to_thread(reap_stuck_jobs, db, older_than=stale_after)
            if reaped:
                logger.warning("Watchdog reaped %d stuck video job(s)", reaped)
        except Exception:
            logger.exception("Watchdog sweep failed")
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

    watchdog_task = asyncio.create_task(_watchdog_loop())
    try:
        yield
    finally:
        watchdog_task.cancel()
        try:
            await watchdog_task
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


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness/readiness check endpoint."""
    return {"status": "ok"}

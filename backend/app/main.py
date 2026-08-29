"""FastAPI application entrypoint for VideoFlipper.

This phase wires up the app instance, CORS, and global exception
handling only. Routers are added in a later phase.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.exceptions import register_exception_handlers
from app.routers import auth, dashboard, videos

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup/shutdown hooks."""
    logger.info("%s starting up", settings.APP_NAME)
    yield
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

"""Application configuration.

Settings are read from environment variables (and a local `.env` file when
present). No secrets are hardcoded here - see `.env.example` for the
expected variable names.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings sourced from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "VideoFlipper"

    # --- Database ---
    DATABASE_URL: str

    # --- JWT auth ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Object storage (for processed video files) ---
    STORAGE_BUCKET: str
    STORAGE_ACCESS_KEY: str
    STORAGE_SECRET_KEY: str

    # --- CORS ---
    # http://localhost:5173 is the Vite dev server; http://localhost (port 80,
    # which browsers omit from the Origin header) is where docker-compose's
    # nginx-served frontend runs by default.
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost"]

    # --- Stuck-job watchdog ---
    # A video stuck in pending/downloading/processing for longer than this
    # is assumed hung (or orphaned by a crashed/restarted worker) and is
    # swept to `failed` by the periodic watchdog. Also applied unconditionally
    # once at startup, since any such row at boot is necessarily orphaned
    # from a previous process.
    STUCK_JOB_TIMEOUT_MINUTES: int = 20
    WATCHDOG_INTERVAL_SECONDS: int = 300

    # --- Storage retention ---
    # Output files for completed/failed jobs older than this are deleted by
    # the periodic maintenance loop (the DB row is kept for history — the
    # download endpoint just 404s once the file is gone). Raw downloaded
    # source files are never persisted past a job's own run in the first
    # place (see video_service.process_video_job), so this only bounds
    # `output.mp4` growth in backend/storage/.
    STORAGE_RETENTION_DAYS: int = 30


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance.

    Cached so environment variables are parsed once per process rather
    than on every access.
    """
    return Settings()

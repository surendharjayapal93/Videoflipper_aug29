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
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    """Return a cached `Settings` instance.

    Cached so environment variables are parsed once per process rather
    than on every access.
    """
    return Settings()

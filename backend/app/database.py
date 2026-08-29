"""Database engine, session factory, and FastAPI dependency.

`DATABASE_URL` is read from the environment via `app.config.get_settings`
(backed by pydantic-settings, which also loads a local `.env` file).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for the duration of a request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""Shared pytest fixtures for the VideoFlipper backend test suite.

Test database strategy
-----------------------
Tests run against an in-memory SQLite database instead of the real
Postgres instance `app.config.Settings` expects in production. Required
settings that have no default (``DATABASE_URL``, ``SECRET_KEY``,
``STORAGE_BUCKET``, ``STORAGE_ACCESS_KEY``, ``STORAGE_SECRET_KEY``) are
set as environment variables *before* anything under ``app`` is imported,
so `app.config.get_settings()` never needs a real `.env` file to
construct successfully in CI.

`app.services.video_service.process_video_job` opens its own
`SessionLocal()` because it runs as a FastAPI `BackgroundTasks` callback
outside of the request lifecycle -- so a `get_db` dependency override
alone would not be enough to point it at the test database. Instead this
file replaces `app.database.engine` with a SQLite engine and reconfigures
the *existing* `SessionLocal` sessionmaker object in place (rather than
creating a new one) so every session -- whether obtained through the
`get_db` dependency or created directly via `SessionLocal()` inside a
background job -- binds to the same engine.

The engine uses `StaticPool` so all checkouts share a single physical
SQLite connection (the default pool would otherwise hand out separate
`:memory:` databases per connection, wiping data between checkouts).
Tables are created fresh before each test and dropped afterward
(`_fresh_schema`, autouse) so tests never leak data into one another.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

# --- Must happen before any `import app...` -------------------------------
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")
os.environ.setdefault("STORAGE_BUCKET", "test-bucket")
os.environ.setdefault("STORAGE_ACCESS_KEY", "test-access-key")
os.environ.setdefault("STORAGE_SECRET_KEY", "test-storage-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.database as database_module
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.video import Video  # noqa: F401

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
# Reconfigure in place: `video_service.py` does `from app.database import
# SessionLocal`, binding its own module-level name to this exact
# sessionmaker object, so mutating it here also redirects that caller.
database_module.engine = TEST_ENGINE
database_module.SessionLocal.configure(bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def _fresh_schema() -> Iterator[None]:
    """Create all tables before each test, drop them afterward."""
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Clear the in-memory auth rate limiter's hit counters between tests.

    `app.auth.rate_limit` keeps its `_hits` dict at module scope so it can
    persist for the life of the real server process; left alone across
    tests, requests would accumulate under the same `testclient` client
    host and every test after the 5th `/auth/register` or `/auth/login`
    call in the whole run would start seeing 429s.
    """
    from app.auth import rate_limit as rate_limit_module

    rate_limit_module._hits.clear()


@pytest.fixture
def db() -> Iterator[Session]:
    """A SQLAlchemy session bound to the shared in-memory test engine."""
    session = database_module.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """A `TestClient` whose `get_db` dependency is overridden to reuse `db`.

    Reusing the same session that direct-to-DB assertions use means a test
    can make an API call and then immediately query `db` for the resulting
    row without worrying about seeing stale/cached data from a separate
    connection.
    """

    def _override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_credentials() -> dict[str, str]:
    """Default credentials used by `registered_user` / `auth_headers`."""
    return {"email": "test@example.com", "password": "password123", "full_name": "Test User"}


@pytest.fixture
def registered_user(client: TestClient, test_user_credentials: dict[str, str], db: Session) -> User:
    """Register the default test user via the real `/auth/register` endpoint.

    Returns the resulting ORM `User` row (useful for tests that need to
    attach videos to this user directly via `db`).
    """
    response = client.post("/api/v1/auth/register", json=test_user_credentials)
    assert response.status_code == 201, response.text
    user = db.query(User).filter(User.email == test_user_credentials["email"]).first()
    assert user is not None
    return user


@pytest.fixture
def auth_headers(
    client: TestClient, test_user_credentials: dict[str, str], registered_user: User
) -> dict[str, str]:
    """Register (via `registered_user`) + log in the default test user; return Bearer auth headers."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
        },
    )
    assert response.status_code == 200, response.text
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def create_user(client: TestClient, db: Session):
    """Factory fixture: register + log in an arbitrary user.

    Returns a `(User, headers)` tuple. Used by tests that need a *second*
    user distinct from the one `auth_headers` sets up (e.g. ownership /
    cross-user isolation checks).
    """

    def _create(email: str, password: str = "password123", full_name: str | None = "Another User"):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        assert response.status_code == 201, response.text

        login_response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        assert login_response.status_code == 200, login_response.text
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        return user, headers

    return _create

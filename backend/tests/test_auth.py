"""Tests for `/api/v1/auth/*`: register, login, refresh, logout, profile."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


# --- register ---------------------------------------------------------------


def test_register_success(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "password123", "full_name": "New User"},
    )

    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_register_duplicate_email_returns_409(client: TestClient, registered_user) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "anotherpassword"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )

    assert response.status_code == 422


# --- login --------------------------------------------------------------


def test_login_success(client: TestClient, registered_user, test_user_credentials) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_wrong_password_returns_401(
    client: TestClient, registered_user, test_user_credentials
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user_credentials["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_unknown_user_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )

    assert response.status_code == 401


# --- refresh --------------------------------------------------------------


def test_refresh_success_rotates_token(
    client: TestClient, registered_user, test_user_credentials
) -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
        },
    )
    old_refresh_token = login_response.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})

    assert response.status_code == 200
    body = response.json()
    assert body["refresh_token"] != old_refresh_token

    # The old token is revoked (rotation) and can no longer be used again.
    replay_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh_token}
    )
    assert replay_response.status_code == 401


def test_refresh_revoked_token_returns_401(
    client: TestClient, registered_user, test_user_credentials, db: Session
) -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    stored = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    assert stored is not None
    stored.revoked = True
    db.commit()

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 401


def test_refresh_invalid_token_returns_401(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-jwt"})

    assert response.status_code == 401


# --- logout -----------------------------------------------------------------


def test_logout_revokes_refresh_token(
    client: TestClient, registered_user, test_user_credentials
) -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
        },
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_response.status_code == 204

    # The now-revoked token can no longer be exchanged.
    reuse_response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse_response.status_code == 401


def test_logout_unknown_token_is_idempotent(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout", json={"refresh_token": "unknown-token"})

    assert response.status_code == 204


# --- profile (/auth/me) ------------------------------------------------------


def test_get_me_authorized(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "test@example.com"
    assert body["full_name"] == "Test User"


def test_get_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_update_me_changes_full_name(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.put(
        "/api/v1/auth/me", json={"full_name": "Updated Name"}, headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"


def test_protected_route_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/videos")

    assert response.status_code == 401


def test_protected_route_with_malformed_token_returns_401(client: TestClient) -> None:
    response = client.get(
        "/api/v1/videos", headers={"Authorization": "Bearer not-a-real-jwt"}
    )

    assert response.status_code == 401

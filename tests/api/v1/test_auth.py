from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.auth import hash_password
from app.models import User, UserRole, Workspace


def seed_user(fake_session, *, password="SecurePass123!", role=UserRole.USER):
    now = datetime.now(tz=UTC)
    workspace_id = uuid4()
    email = "user@acme.com"
    workspace = Workspace(
        id=workspace_id,
        name="Acme Corp",
        created_at=now,
        updated_at=now,
    )
    user = User(
        id=uuid4(),
        workspace_id=workspace_id,
        email=email,
        full_name="Test User",
        password_hash=hash_password(password),
        role=role,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.workspaces[workspace_id] = workspace
    fake_session.users[(workspace_id, email)] = user
    return workspace, user


def test_login_returns_access_and_refresh_tokens(
    client, fake_session, auth_secret
) -> None:
    _workspace, user = seed_user(fake_session)

    response = client.post(
        "/api/v1/auth/login/",
        json={
            "workspace_id": str(user.workspace_id),
            "email": user.email,
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Login successful."
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["access_token"]
    assert body["data"]["refresh_token"]
    assert body["data"]["access_token"] != body["data"]["refresh_token"]


def test_login_rejects_invalid_password(client, fake_session, auth_secret) -> None:
    _workspace, user = seed_user(fake_session)

    response = client.post(
        "/api/v1/auth/login/",
        json={
            "workspace_id": str(user.workspace_id),
            "email": user.email,
            "password": "WrongPass123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid email or password."


def test_login_rejects_missing_user(client, fake_session, auth_secret) -> None:
    response = client.post(
        "/api/v1/auth/login/",
        json={
            "workspace_id": str(uuid4()),
            "email": "missing@acme.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid email or password."


def test_logout_increments_token_version(client, fake_session, make_token) -> None:
    _workspace, user = seed_user(fake_session)
    token = make_token(
        user_email=user.email,
        workspace_id=user.workspace_id,
        role=user.role,
        token_version=user.token_version,
    )

    response = client.post(
        "/api/v1/auth/logout/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Logout successful."
    assert body["data"]["token_version"] == 1
    assert user.token_version == 1


def test_old_token_fails_after_logout(client, fake_session, make_token) -> None:
    workspace, user = seed_user(fake_session, role=UserRole.ADMIN)
    token = make_token(
        user_email=user.email,
        workspace_id=user.workspace_id,
        role=user.role,
        token_version=user.token_version,
    )

    logout_response = client.post(
        "/api/v1/auth/logout/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200

    response = client.get(
        f"/api/v1/workspaces/{workspace.id}/users/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Access token is no longer valid."

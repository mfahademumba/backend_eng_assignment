from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.models import User, UserRole, Workspace


def test_create_workspace_returns_workspace_and_admin_credentials(client) -> None:
    response = client.post(
        "/api/v1/workspaces/",
        json={
            "name": "Acme Corp",
            "admin_email": "admin@acme.com",
            "admin_password": "SecurePass123!",
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Workspace created successfully."

    data = body["data"]
    assert data["workspace"]["name"] == "Acme Corp"
    assert data["workspace"]["id"]
    assert data["admin_credentials"]["email"] == "admin@acme.com"
    assert data["admin_credentials"]["role"] == "admin"
    assert "admin_password" not in data


def test_create_workspace_rejects_weak_password(client) -> None:
    response = client.post(
        "/api/v1/workspaces/",
        json={
            "name": "Acme Corp",
            "admin_email": "admin@acme.com",
            "admin_password": "weakpass1",
        },
    )

    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Validation failed."
    assert any(
        error["field"] == "body.admin_password"
        and "uppercase" in error["detail"].lower()
        for error in body["errors"]
    )


def test_get_workspace_details_returns_200_for_admin(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_id = uuid4()
    user_email = "admin@acme.com"
    now = datetime.now(tz=UTC)

    workspace = Workspace(
        id=workspace_id,
        name="Acme Corp",
        created_at=now,
        updated_at=now,
    )
    admin_user = User(
        id=uuid4(),
        workspace_id=workspace_id,
        email=user_email,
        password_hash="hashed-password",
        role=UserRole.ADMIN,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.workspaces[workspace_id] = workspace
    fake_session.scalar_result = admin_user

    token = make_token(
        user_email=user_email,
        workspace_id=workspace_id,
        role=UserRole.ADMIN,
    )

    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Workspace retrieved successfully."
    assert body["data"]["workspace"]["id"] == str(workspace_id)
    assert body["data"]["workspace"]["name"] == "Acme Corp"


def test_get_workspace_details_returns_403_for_non_admin_user(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_id = uuid4()
    user_email = "member@acme.com"
    now = datetime.now(tz=UTC)

    workspace = Workspace(
        id=workspace_id,
        name="Acme Corp",
        created_at=now,
        updated_at=now,
    )
    regular_user = User(
        id=uuid4(),
        workspace_id=workspace_id,
        email=user_email,
        password_hash="hashed-password",
        role=UserRole.USER,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.workspaces[workspace_id] = workspace
    fake_session.scalar_result = regular_user

    token = make_token(
        user_email=user_email,
        workspace_id=workspace_id,
        role=UserRole.USER,
    )

    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403

    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Admin access is required."

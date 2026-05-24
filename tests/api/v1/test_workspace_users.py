from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.models import User, UserRole, Workspace


def seed_workspace_with_admin(fake_session, workspace_id, admin_email="admin@acme.com"):
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
        email=admin_email,
        full_name="Admin User",
        password_hash="hashed-password",
        role=UserRole.ADMIN,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.workspaces[workspace_id] = workspace
    fake_session.users[(workspace_id, admin_email)] = admin_user
    fake_session.scalar_result = admin_user
    return workspace, admin_user


def test_create_workspace_user_returns_created_user(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_id = uuid4()
    _workspace, admin_user = seed_workspace_with_admin(fake_session, workspace_id)
    token = make_token(
        user_email=admin_user.email,
        workspace_id=workspace_id,
        role=UserRole.ADMIN,
    )

    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/users/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "user@acme.com",
            "password": "SecurePass123!",
            "role": "user",
            "full_name": "John Doe",
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "User created successfully."

    user = body["data"]["user"]
    assert user["email"] == "user@acme.com"
    assert user["full_name"] == "John Doe"
    assert user["role"] == "user"
    assert user["workspace_id"] == str(workspace_id)
    assert "password" not in user
    assert "password_hash" not in user

    created_user = fake_session.users[(workspace_id, "user@acme.com")]
    assert created_user.password_hash != "SecurePass123!"


def test_create_workspace_user_rejects_weak_password(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_id = uuid4()
    _workspace, admin_user = seed_workspace_with_admin(fake_session, workspace_id)
    token = make_token(
        user_email=admin_user.email,
        workspace_id=workspace_id,
        role=UserRole.ADMIN,
    )

    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/users/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "user@acme.com",
            "password": "weakpass1",
            "role": "user",
            "full_name": "John Doe",
        },
    )

    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Validation failed."
    assert body["data"] is None
    assert any(
        error["field"] == "body.password"
        and error["code"] == "validation_error"
        and "uppercase" in error["detail"].lower()
        for error in body["errors"]
    )


def test_workspace_user_routes_openapi_document_payload_error_responses(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    create_responses = paths["/api/v1/workspaces/{workspace_id}/users/"]["post"][
        "responses"
    ]
    update_responses = paths["/api/v1/workspaces/{workspace_id}/users/{user_id}/"][
        "patch"
    ]["responses"]

    assert "400" in create_responses
    assert "422" in create_responses
    assert "400" in update_responses
    assert "422" in update_responses


def test_create_workspace_user_returns_403_for_non_admin(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_id = uuid4()
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
        email="member@acme.com",
        full_name="Member User",
        password_hash="hashed-password",
        role=UserRole.USER,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.workspaces[workspace_id] = workspace
    fake_session.users[(workspace_id, regular_user.email)] = regular_user
    fake_session.scalar_result = regular_user
    token = make_token(
        user_email=regular_user.email,
        workspace_id=workspace_id,
        role=UserRole.USER,
    )

    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/users/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "user@acme.com",
            "password": "SecurePass123!",
            "role": "user",
            "full_name": "John Doe",
        },
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Admin access is required."


def test_list_workspace_users_returns_users(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_id = uuid4()
    _workspace, admin_user = seed_workspace_with_admin(fake_session, workspace_id)
    now = datetime.now(tz=UTC)
    member_user = User(
        id=uuid4(),
        workspace_id=workspace_id,
        email="user@acme.com",
        full_name="John Doe",
        password_hash="hashed-password",
        role=UserRole.USER,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.users[(workspace_id, member_user.email)] = member_user
    token = make_token(
        user_email=admin_user.email,
        workspace_id=workspace_id,
        role=UserRole.ADMIN,
    )

    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/users/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Users retrieved successfully."
    assert [user["email"] for user in body["data"]["users"]] == [
        "admin@acme.com",
        "user@acme.com",
    ]


def test_update_workspace_user_role_updates_user(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_id = uuid4()
    _workspace, admin_user = seed_workspace_with_admin(fake_session, workspace_id)
    now = datetime.now(tz=UTC)
    member_user = User(
        id=uuid4(),
        workspace_id=workspace_id,
        email="user@acme.com",
        full_name="John Doe",
        password_hash="hashed-password",
        role=UserRole.USER,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.users[(workspace_id, member_user.email)] = member_user
    token = make_token(
        user_email=admin_user.email,
        workspace_id=workspace_id,
        role=UserRole.ADMIN,
    )

    response = client.patch(
        f"/api/v1/workspaces/{workspace_id}/users/{member_user.id}/",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "admin"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "User role updated successfully."
    assert body["data"]["user"]["role"] == "admin"
    assert member_user.role == UserRole.ADMIN


def test_update_workspace_user_role_returns_404_for_missing_user(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_id = uuid4()
    _workspace, admin_user = seed_workspace_with_admin(fake_session, workspace_id)
    token = make_token(
        user_email=admin_user.email,
        workspace_id=workspace_id,
        role=UserRole.ADMIN,
    )

    response = client.patch(
        f"/api/v1/workspaces/{workspace_id}/users/{uuid4()}/",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "admin"},
    )

    assert response.status_code == 404
    assert response.json()["message"] == "User not found."

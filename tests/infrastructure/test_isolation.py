from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.models import Resource, User, UserRole, Workspace


def seed_workspace_with_user(
    fake_session,
    *,
    email: str,
    role: UserRole = UserRole.USER,
    name: str = "Workspace",
):
    now = datetime.now(tz=UTC)
    workspace = Workspace(
        id=uuid4(),
        name=name,
        created_at=now,
        updated_at=now,
    )
    user = User(
        id=uuid4(),
        workspace_id=workspace.id,
        email=email,
        full_name="Test User",
        password_hash="hashed-password",
        role=role,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.workspaces[workspace.id] = workspace
    fake_session.users[(workspace.id, user.email)] = user
    return workspace, user


def seed_resource(fake_session, *, workspace_id, name: str):
    now = datetime.now(tz=UTC)
    resource = Resource(
        id=uuid4(),
        workspace_id=workspace_id,
        name=name,
        type="database",
        description=None,
        status="active",
        created_at=now,
        updated_at=now,
    )
    fake_session.resources[resource.id] = resource
    return resource


def test_user_in_one_workspace_cannot_access_another_workspace_resource_details(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_a, user_a = seed_workspace_with_user(
        fake_session, email="user@a.com", name="Workspace A"
    )
    workspace_b, _user_b = seed_workspace_with_user(
        fake_session, email="user@b.com", name="Workspace B"
    )
    resource_b = seed_resource(
        fake_session, workspace_id=workspace_b.id, name="Workspace B DB"
    )
    token = make_token(
        user_email=user_a.email,
        workspace_id=workspace_a.id,
        role=user_a.role,
    )

    response = client.get(
        f"/api/v1/workspaces/{workspace_a.id}/resources/{resource_b.id}/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Resource not found."


def test_user_in_one_workspace_cannot_call_another_workspace_resource_route(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_a, user_a = seed_workspace_with_user(
        fake_session, email="user@a.com", name="Workspace A"
    )
    workspace_b, _user_b = seed_workspace_with_user(
        fake_session, email="user@b.com", name="Workspace B"
    )
    seed_resource(fake_session, workspace_id=workspace_b.id, name="Workspace B DB")
    token = make_token(
        user_email=user_a.email,
        workspace_id=workspace_a.id,
        role=user_a.role,
    )

    response = client.get(
        f"/api/v1/workspaces/{workspace_b.id}/resources/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["message"] == "You do not have access to this workspace."


def test_admin_lists_only_users_from_requested_workspace(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_a, admin_a = seed_workspace_with_user(
        fake_session,
        email="admin@a.com",
        role=UserRole.ADMIN,
        name="Workspace A",
    )
    workspace_b, _admin_b = seed_workspace_with_user(
        fake_session,
        email="admin@b.com",
        role=UserRole.ADMIN,
        name="Workspace B",
    )
    seed_workspace_with_user(fake_session, email="member@a.com", name="Workspace A")
    # Move the second member into workspace A because the helper creates a workspace.
    stray_workspace_id = next(
        workspace_id
        for workspace_id, workspace in fake_session.workspaces.items()
        if workspace.name == "Workspace A" and workspace_id != workspace_a.id
    )
    member_a = fake_session.users.pop((stray_workspace_id, "member@a.com"))
    member_a.workspace_id = workspace_a.id
    fake_session.users[(workspace_a.id, member_a.email)] = member_a
    token = make_token(
        user_email=admin_a.email,
        workspace_id=workspace_a.id,
        role=admin_a.role,
    )

    response = client.get(
        f"/api/v1/workspaces/{workspace_a.id}/users/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    emails = [user["email"] for user in response.json()["data"]["users"]]
    assert emails == ["admin@a.com", "member@a.com"]
    assert "admin@b.com" not in emails
    assert workspace_b.id != workspace_a.id


def test_admin_in_one_workspace_cannot_manage_another_workspace_users_route(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_a, admin_a = seed_workspace_with_user(
        fake_session,
        email="admin@a.com",
        role=UserRole.ADMIN,
        name="Workspace A",
    )
    workspace_b, _admin_b = seed_workspace_with_user(
        fake_session,
        email="admin@b.com",
        role=UserRole.ADMIN,
        name="Workspace B",
    )
    token = make_token(
        user_email=admin_a.email,
        workspace_id=workspace_a.id,
        role=admin_a.role,
    )

    response = client.post(
        f"/api/v1/workspaces/{workspace_b.id}/users/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "new@b.com",
            "password": "SecurePass123!",
            "role": "user",
            "full_name": "New User",
        },
    )

    assert response.status_code == 403
    assert response.json()["message"] == "You do not have access to this workspace."
    assert (workspace_b.id, "new@b.com") not in fake_session.users

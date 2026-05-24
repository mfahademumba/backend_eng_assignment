from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.models import (
    EffectivePolicy,
    Policy,
    PolicyEffect,
    Resource,
    User,
    UserRole,
    Workspace,
)


def seed_workspace_user_resource(fake_session, *, user_role=UserRole.USER):
    now = datetime.now(tz=UTC)
    workspace_id = uuid4()
    workspace = Workspace(
        id=workspace_id, name="Acme Corp", created_at=now, updated_at=now
    )
    user = User(
        id=uuid4(),
        workspace_id=workspace_id,
        email="user@acme.com",
        full_name="User",
        password_hash="hashed-password",
        role=user_role,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    resource = Resource(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Production DB",
        type="database",
        status="active",
        description=None,
        created_at=now,
        updated_at=now,
    )
    fake_session.workspaces[workspace_id] = workspace
    fake_session.users[(workspace_id, user.email)] = user
    fake_session.resources[resource.id] = resource
    return workspace, user, resource


def seed_policy(
    fake_session,
    *,
    workspace_id,
    resource_id,
    name,
    effect,
    target_type,
    target_value,
    priority,
):
    now = datetime.now(tz=UTC)
    policy = Policy(
        id=uuid4(),
        workspace_id=workspace_id,
        name=name,
        effect=effect,
        target_type=target_type,
        target_value=target_value,
        priority=priority,
        created_at=now,
        updated_at=now,
    )
    effective_policy = EffectivePolicy(
        id=uuid4(),
        workspace_id=workspace_id,
        resource_id=resource_id,
        policy_id=policy.id,
        created_at=now,
        updated_at=now,
    )
    effective_policy.policy = policy
    fake_session.policies[policy.id] = policy
    fake_session.effective_policies[effective_policy.id] = effective_policy
    return policy


def test_access_check_admin_bypasses_policy_evaluation(
    client, fake_session, make_token
) -> None:
    workspace, admin_user, resource = seed_workspace_user_resource(
        fake_session, user_role=UserRole.ADMIN
    )
    seed_policy(
        fake_session,
        workspace_id=workspace.id,
        resource_id=resource.id,
        name="Deny admins",
        effect=PolicyEffect.DENY,
        target_type="role",
        target_value="admin",
        priority=100,
    )

    token = make_token(
        user_email=admin_user.email,
        workspace_id=workspace.id,
        role=admin_user.role,
    )

    response = client.post(
        "/api/v1/access-check/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspace_id": str(workspace.id),
            "user_id": str(admin_user.id),
            "resource_id": str(resource.id),
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "access_granted": True,
        "reason": "Admin bypass: admins always have access to resources in their workspace",
        "matched_policy_id": None,
    }


def test_access_check_admin_can_check_another_user_in_same_workspace(
    client, fake_session, make_token
) -> None:
    workspace, admin_user, resource = seed_workspace_user_resource(
        fake_session, user_role=UserRole.ADMIN
    )
    now = datetime.now(tz=UTC)
    member_user = User(
        id=uuid4(),
        workspace_id=workspace.id,
        email="member@acme.com",
        full_name="Member",
        password_hash="hashed-password",
        role=UserRole.USER,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.users[(workspace.id, member_user.email)] = member_user
    token = make_token(
        user_email=admin_user.email,
        workspace_id=workspace.id,
        role=admin_user.role,
    )

    response = client.post(
        "/api/v1/access-check/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspace_id": str(workspace.id),
            "user_id": str(member_user.id),
            "resource_id": str(resource.id),
        },
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "access_granted": False,
        "reason": "No matching policy found. Access denied by default.",
        "matched_policy_id": None,
    }


def test_access_check_uses_highest_priority_matching_policy(
    client, fake_session, make_token
) -> None:
    workspace, user, resource = seed_workspace_user_resource(fake_session)
    seed_policy(
        fake_session,
        workspace_id=workspace.id,
        resource_id=resource.id,
        name="Allow users",
        effect=PolicyEffect.ALLOW,
        target_type="role",
        target_value="user",
        priority=10,
    )
    deny_policy = seed_policy(
        fake_session,
        workspace_id=workspace.id,
        resource_id=resource.id,
        name="Deny specific user",
        effect=PolicyEffect.DENY,
        target_type="user",
        target_value=str(user.id),
        priority=20,
    )
    token = make_token(
        user_email=user.email,
        workspace_id=workspace.id,
        role=user.role,
    )

    response = client.post(
        "/api/v1/access-check/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspace_id": str(workspace.id),
            "user_id": str(user.id),
            "resource_id": str(resource.id),
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access_granted"] is False
    assert data["reason"] == "Matched policy: Deny specific user (priority 20)"
    assert data["matched_policy_id"] == str(deny_policy.id)


def test_access_check_returns_403_when_non_admin_checks_another_same_workspace_user(
    client, fake_session, make_token
) -> None:
    workspace, user, resource = seed_workspace_user_resource(fake_session)
    now = datetime.now(tz=UTC)
    other_user = User(
        id=uuid4(),
        workspace_id=workspace.id,
        email="other@acme.com",
        full_name="Other User",
        password_hash="hashed-password",
        role=UserRole.USER,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.users[(workspace.id, other_user.email)] = other_user
    token = make_token(
        user_email=user.email,
        workspace_id=workspace.id,
        role=user.role,
    )

    response = client.post(
        "/api/v1/access-check/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspace_id": str(workspace.id),
            "user_id": str(other_user.id),
            "resource_id": str(resource.id),
        },
    )

    assert response.status_code == 403
    assert response.json()["message"] == "You can only check your own access."


def test_access_check_returns_403_for_user_from_another_workspace(
    client, fake_session, make_token
) -> None:
    workspace, user, resource = seed_workspace_user_resource(fake_session)
    other_workspace, other_user, _other_resource = seed_workspace_user_resource(
        fake_session
    )
    token = make_token(
        user_email=user.email,
        workspace_id=workspace.id,
        role=user.role,
    )

    response = client.post(
        "/api/v1/access-check/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspace_id": str(other_workspace.id),
            "user_id": str(other_user.id),
            "resource_id": str(resource.id),
        },
    )

    assert response.status_code == 403
    assert response.json()["message"] == "You do not have access to this workspace."


def test_access_check_returns_404_for_resource_from_another_workspace(
    client, fake_session, make_token
) -> None:
    workspace, user, _resource = seed_workspace_user_resource(fake_session)
    other_workspace, _other_user, other_resource = seed_workspace_user_resource(
        fake_session
    )
    token = make_token(
        user_email=user.email,
        workspace_id=workspace.id,
        role=user.role,
    )

    response = client.post(
        "/api/v1/access-check/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspace_id": str(workspace.id),
            "user_id": str(user.id),
            "resource_id": str(other_resource.id),
        },
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Resource not found."
    assert other_workspace.id != workspace.id


def test_access_check_returns_401_without_authentication(client, fake_session) -> None:
    workspace, user, resource = seed_workspace_user_resource(fake_session)

    response = client.post(
        "/api/v1/access-check/",
        json={
            "workspace_id": str(workspace.id),
            "user_id": str(user.id),
            "resource_id": str(resource.id),
        },
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Authentication credentials were not provided."


def test_access_check_denies_by_default_when_no_policy_matches(
    client, fake_session, make_token
) -> None:
    workspace, user, resource = seed_workspace_user_resource(fake_session)
    token = make_token(
        user_email=user.email,
        workspace_id=workspace.id,
        role=user.role,
    )

    response = client.post(
        "/api/v1/access-check/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspace_id": str(workspace.id),
            "user_id": str(user.id),
            "resource_id": str(resource.id),
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data == {
        "access_granted": False,
        "reason": "No matching policy found. Access denied by default.",
        "matched_policy_id": None,
    }

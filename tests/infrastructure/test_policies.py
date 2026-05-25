from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.infrastructure.repositories.policy_repository import PolicyRepository
from app.models import (
    EffectivePolicy,
    Policy,
    PolicyEffect,
    Resource,
    User,
    UserRole,
    Workspace,
)


def seed_workspace_admin_resource(fake_session):
    now = datetime.now(tz=UTC)
    workspace_id = uuid4()
    workspace = Workspace(
        id=workspace_id, name="Acme Corp", created_at=now, updated_at=now
    )
    admin_user = User(
        id=uuid4(),
        workspace_id=workspace_id,
        email="admin@acme.com",
        full_name="Admin User",
        password_hash="hashed-password",
        role=UserRole.ADMIN,
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
    fake_session.users[(workspace_id, admin_user.email)] = admin_user
    fake_session.resources[resource.id] = resource
    fake_session.scalar_result = admin_user
    return workspace, admin_user, resource


def test_admin_can_create_list_and_delete_resource_policy(
    client, fake_session, make_token
) -> None:
    workspace, admin_user, resource = seed_workspace_admin_resource(fake_session)
    token = make_token(
        user_email=admin_user.email,
        workspace_id=workspace.id,
        role=UserRole.ADMIN,
    )

    create_response = client.post(
        f"/api/v1/workspaces/{workspace.id}/resources/{resource.id}/policies/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Allow developers",
            "effect": "allow",
            "target_type": "role",
            "target_value": "user",
            "priority": 10,
        },
    )

    assert create_response.status_code == 201
    created_policy = create_response.json()["data"]["policy"]
    assert created_policy["name"] == "Allow developers"
    assert created_policy["effect"] == "allow"
    assert created_policy["target_type"] == "role"
    assert created_policy["target_value"] == "user"
    assert created_policy["priority"] == 10

    list_response = client.get(
        f"/api/v1/workspaces/{workspace.id}/resources/{resource.id}/policies/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert list_response.status_code == 200
    policies = list_response.json()["data"]["policies"]
    assert [policy["id"] for policy in policies] == [created_policy["id"]]

    delete_response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/resources/{resource.id}/policies/{created_policy['id']}/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert delete_response.status_code == 204
    assert not delete_response.content
    assert created_policy["id"] not in {
        str(policy_id) for policy_id in fake_session.policies
    }


def test_non_admin_cannot_create_resource_policy(
    client, fake_session, make_token
) -> None:
    workspace, _admin_user, resource = seed_workspace_admin_resource(fake_session)
    regular_user = User(
        id=uuid4(),
        workspace_id=workspace.id,
        email="member@acme.com",
        full_name="Member User",
        password_hash="hashed-password",
        role=UserRole.USER,
        token_version=0,
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
    )
    fake_session.users[(workspace.id, regular_user.email)] = regular_user
    fake_session.scalar_result = regular_user
    token = make_token(
        user_email=regular_user.email,
        workspace_id=workspace.id,
        role=UserRole.USER,
    )

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/resources/{resource.id}/policies/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Allow developers",
            "effect": "allow",
            "target_type": "role",
            "target_value": "user",
            "priority": 10,
        },
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Admin access is required."


def test_create_policy_returns_404_for_nonexistent_resource(
    client, fake_session, make_token
) -> None:
    workspace, admin_user, _resource = seed_workspace_admin_resource(fake_session)
    missing_resource_id = uuid4()
    token = make_token(
        user_email=admin_user.email,
        workspace_id=workspace.id,
        role=UserRole.ADMIN,
    )

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/resources/{missing_resource_id}/policies/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Allow developers",
            "effect": "allow",
            "target_type": "role",
            "target_value": "user",
            "priority": 10,
        },
    )

    assert response.status_code == 404
    assert response.json()["message"] == "Resource not found."
    assert not any(
        policy.name == "Allow developers" for policy in fake_session.policies.values()
    )


def test_policy_create_validates_user_target_uuid(
    client, fake_session, make_token
) -> None:
    workspace, admin_user, resource = seed_workspace_admin_resource(fake_session)
    token = make_token(
        user_email=admin_user.email,
        workspace_id=workspace.id,
        role=UserRole.ADMIN,
    )

    response = client.post(
        f"/api/v1/workspaces/{workspace.id}/resources/{resource.id}/policies/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Allow specific user",
            "effect": "allow",
            "target_type": "user",
            "target_value": "not-a-uuid",
            "priority": 20,
        },
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Validation failed."


@pytest.mark.anyio
async def test_repository_delete_for_resource_does_not_delete_wrong_resource_policy(
    fake_session,
) -> None:
    workspace, _admin_user, resource = seed_workspace_admin_resource(fake_session)
    now = datetime.now(tz=UTC)
    other_resource = Resource(
        id=uuid4(),
        workspace_id=workspace.id,
        name="Staging DB",
        type="database",
        status="active",
        description=None,
        created_at=now,
        updated_at=now,
    )
    policy = Policy(
        id=uuid4(),
        workspace_id=workspace.id,
        name="Allow developers",
        effect=PolicyEffect.ALLOW,
        target_type="role",
        target_value="user",
        priority=10,
        created_at=now,
        updated_at=now,
    )
    effective_policy = EffectivePolicy(
        id=uuid4(),
        workspace_id=workspace.id,
        resource_id=resource.id,
        policy_id=policy.id,
        created_at=now,
        updated_at=now,
    )
    effective_policy.policy = policy
    fake_session.resources[other_resource.id] = other_resource
    fake_session.policies[policy.id] = policy
    fake_session.effective_policies[effective_policy.id] = effective_policy

    repository = PolicyRepository(fake_session)
    await repository.delete_for_resource(
        workspace_id=workspace.id,
        resource_id=other_resource.id,
        policy_id=policy.id,
    )

    assert policy.id in fake_session.policies
    assert effective_policy.id in fake_session.effective_policies

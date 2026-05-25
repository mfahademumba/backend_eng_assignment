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


def seed_user(
    fake_session, *, workspace_id, role=UserRole.ADMIN, email="admin@acme.com"
):
    now = datetime.now(tz=UTC)
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
        password_hash="hashed-password",
        role=role,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.workspaces[workspace_id] = workspace
    fake_session.users[(workspace_id, email)] = user
    return user


def seed_resource(fake_session, *, workspace_id, name="Customer Database"):
    now = datetime.now(tz=UTC)
    resource = Resource(
        id=uuid4(),
        workspace_id=workspace_id,
        name=name,
        type="database",
        description="Production customer data",
        status="active",
        created_at=now,
        updated_at=now,
    )
    fake_session.resources[resource.id] = resource
    return resource


def attach_policy(
    fake_session,
    *,
    workspace_id,
    resource_id,
    target_type,
    target_value,
    effect=PolicyEffect.ALLOW,
):
    now = datetime.now(tz=UTC)
    policy = Policy(
        id=uuid4(),
        workspace_id=workspace_id,
        name="Allow access",
        effect=effect,
        target_type=target_type,
        target_value=target_value,
        priority=10,
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


def test_admin_can_create_resource(client, fake_session, make_token) -> None:
    workspace_id = uuid4()
    admin = seed_user(fake_session, workspace_id=workspace_id)
    token = make_token(
        user_email=admin.email, workspace_id=workspace_id, role=admin.role
    )

    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/resources/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Customer Database",
            "type": "database",
            "description": "Production customer data",
            "status": "active",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Resource created successfully."
    assert body["data"]["resource"]["workspace_id"] == str(workspace_id)
    assert body["data"]["resource"]["name"] == "Customer Database"


def test_regular_user_cannot_create_resource(client, fake_session, make_token) -> None:
    workspace_id = uuid4()
    user = seed_user(
        fake_session,
        workspace_id=workspace_id,
        role=UserRole.USER,
        email="member@acme.com",
    )
    token = make_token(user_email=user.email, workspace_id=workspace_id, role=user.role)

    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/resources/",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "DB", "type": "database", "status": "active"},
    )

    assert response.status_code == 403
    assert response.json()["message"] == "Admin access is required."


def test_admin_lists_all_resources(client, fake_session, make_token) -> None:
    workspace_id = uuid4()
    admin = seed_user(fake_session, workspace_id=workspace_id)
    seed_resource(fake_session, workspace_id=workspace_id, name="A Database")
    seed_resource(fake_session, workspace_id=workspace_id, name="B Bucket")
    token = make_token(
        user_email=admin.email, workspace_id=workspace_id, role=admin.role
    )

    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/resources/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert [resource["name"] for resource in response.json()["data"]["resources"]] == [
        "A Database",
        "B Bucket",
    ]


def test_regular_user_lists_only_accessible_resources(
    client, fake_session, make_token
) -> None:
    workspace_id = uuid4()
    user = seed_user(
        fake_session,
        workspace_id=workspace_id,
        role=UserRole.USER,
        email="member@acme.com",
    )
    allowed = seed_resource(fake_session, workspace_id=workspace_id, name="Allowed DB")
    seed_resource(fake_session, workspace_id=workspace_id, name="Denied DB")
    attach_policy(
        fake_session,
        workspace_id=workspace_id,
        resource_id=allowed.id,
        target_type="user",
        target_value=str(user.id),
    )
    token = make_token(user_email=user.email, workspace_id=workspace_id, role=user.role)

    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/resources/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    resources = response.json()["data"]["resources"]
    assert [resource["id"] for resource in resources] == [str(allowed.id)]


def test_resource_details_include_policies_for_authorized_user(
    client, fake_session, make_token
) -> None:
    workspace_id = uuid4()
    user = seed_user(
        fake_session,
        workspace_id=workspace_id,
        role=UserRole.USER,
        email="member@acme.com",
    )
    resource = seed_resource(fake_session, workspace_id=workspace_id)
    policy = attach_policy(
        fake_session,
        workspace_id=workspace_id,
        resource_id=resource.id,
        target_type="role",
        target_value="user",
    )
    token = make_token(user_email=user.email, workspace_id=workspace_id, role=user.role)

    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/resources/{resource.id}/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resource"]["id"] == str(resource.id)
    assert data["policies"][0]["id"] == str(policy.id)


def test_resource_details_forbidden_without_permission(
    client, fake_session, make_token
) -> None:
    workspace_id = uuid4()
    user = seed_user(
        fake_session,
        workspace_id=workspace_id,
        role=UserRole.USER,
        email="member@acme.com",
    )
    resource = seed_resource(fake_session, workspace_id=workspace_id)
    token = make_token(user_email=user.email, workspace_id=workspace_id, role=user.role)

    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/resources/{resource.id}/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["message"] == "You do not have access to this resource."


def test_admin_can_update_and_delete_resource(client, fake_session, make_token) -> None:
    workspace_id = uuid4()
    admin = seed_user(fake_session, workspace_id=workspace_id)
    resource = seed_resource(fake_session, workspace_id=workspace_id)
    token = make_token(
        user_email=admin.email, workspace_id=workspace_id, role=admin.role
    )

    update_response = client.patch(
        f"/api/v1/workspaces/{workspace_id}/resources/{resource.id}/",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "inactive"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["data"]["resource"]["status"] == "inactive"
    assert resource.status == "inactive"

    delete_response = client.delete(
        f"/api/v1/workspaces/{workspace_id}/resources/{resource.id}/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert delete_response.status_code == 204
    assert not delete_response.content
    assert resource.id not in fake_session.resources


def test_deleting_resource_cascades_to_effective_policies(
    client, fake_session, make_token
) -> None:
    workspace_id = uuid4()
    admin = seed_user(fake_session, workspace_id=workspace_id)
    resource = seed_resource(fake_session, workspace_id=workspace_id)
    policy = attach_policy(
        fake_session,
        workspace_id=workspace_id,
        resource_id=resource.id,
        target_type="role",
        target_value="user",
    )
    token = make_token(
        user_email=admin.email, workspace_id=workspace_id, role=admin.role
    )

    response = client.delete(
        f"/api/v1/workspaces/{workspace_id}/resources/{resource.id}/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 204
    assert not response.content
    assert resource.id not in fake_session.resources
    assert policy.id not in fake_session.policies
    assert not any(
        effective_policy.resource_id == resource.id
        for effective_policy in fake_session.effective_policies.values()
    )

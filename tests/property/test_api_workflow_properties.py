from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.models import (
    EffectivePolicy,
    Policy,
    PolicyEffect,
    Resource,
    User,
    UserRole,
    Workspace,
)

safe_text = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_",
    min_size=1,
    max_size=40,
).filter(lambda value: value.strip() != "")
workspace_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_",
    min_size=3,
    max_size=40,
).filter(lambda value: value.strip() != "")
resource_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_",
    min_size=3,
    max_size=40,
).filter(lambda value: value.strip() != "")
roles = st.sampled_from(list(UserRole))
policy_effects = st.sampled_from(list(PolicyEffect))
workflow_settings = settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
small_workflow_settings = settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


def _reset_fake_session(fake_session) -> None:
    fake_session.added_objects = []
    fake_session.workspaces = {}
    fake_session.users = {}
    fake_session.resources = {}
    fake_session.policies = {}
    fake_session.effective_policies = {}
    fake_session.scalar_result = None


def _seed_workspace_user(
    fake_session,
    *,
    role: UserRole = UserRole.ADMIN,
    email: str = "admin@example.com",
) -> tuple[Workspace, User]:
    now = datetime.now(tz=UTC)
    workspace = Workspace(
        id=uuid4(),
        name=f"Workspace {uuid4()}",
        created_at=now,
        updated_at=now,
    )
    user = User(
        id=uuid4(),
        workspace_id=workspace.id,
        email=email,
        full_name="Generated User",
        password_hash="hashed-password",
        role=role,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.workspaces[workspace.id] = workspace
    fake_session.users[(workspace.id, user.email)] = user
    fake_session.scalar_result = user
    return workspace, user


def _seed_resource(
    fake_session, *, workspace_id, name: str = "Generated Resource"
) -> Resource:
    now = datetime.now(tz=UTC)
    resource = Resource(
        id=uuid4(),
        workspace_id=workspace_id,
        name=name,
        type="database",
        description="Generated resource",
        status="active",
        created_at=now,
        updated_at=now,
    )
    fake_session.resources[resource.id] = resource
    return resource


def _attach_policy(
    fake_session,
    *,
    workspace_id,
    resource_id,
    effect: PolicyEffect,
    target_type: str,
    target_value: str,
    priority: int = 10,
) -> Policy:
    now = datetime.now(tz=UTC)
    policy = Policy(
        id=uuid4(),
        workspace_id=workspace_id,
        name=f"{effect.value} generated access",
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


@given(name=workspace_names)
@workflow_settings
def test_generated_workspace_create_and_details_workflow(
    client, fake_session, make_token, name: str
) -> None:
    _reset_fake_session(fake_session)
    create_response = client.post(
        "/api/v1/workspaces/",
        json={
            "name": name,
            "admin_email": "admin@example.com",
            "admin_password": "SecurePass123!",
        },
    )

    assert create_response.status_code == 201
    workspace_id = create_response.json()["data"]["workspace"]["id"]
    admin = fake_session.users[
        (next(iter(fake_session.workspaces)), "admin@example.com")
    ]
    admin.token_version = 0
    token = make_token(
        user_email=admin.email, workspace_id=admin.workspace_id, role=admin.role
    )

    details_response = client.get(
        f"/api/v1/workspaces/{workspace_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert details_response.status_code == 200
    assert details_response.json()["data"]["workspace"]["name"] == name


@given(full_name=safe_text, role=roles)
@workflow_settings
def test_generated_workspace_user_create_list_and_update_workflow(
    client,
    fake_session,
    make_token,
    full_name: str,
    role: UserRole,
) -> None:
    _reset_fake_session(fake_session)
    workspace, admin = _seed_workspace_user(fake_session)
    token = make_token(
        user_email=admin.email, workspace_id=workspace.id, role=admin.role
    )

    create_response = client.post(
        f"/api/v1/workspaces/{workspace.id}/users/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "member@example.com",
            "password": "SecurePass123!",
            "role": role.value,
            "full_name": full_name,
        },
    )

    assert create_response.status_code == 201
    created_user_id = create_response.json()["data"]["user"]["id"]

    list_response = client.get(
        f"/api/v1/workspaces/{workspace.id}/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]["users"]) == 2

    update_response = client.patch(
        f"/api/v1/workspaces/{workspace.id}/users/{created_user_id}/",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": UserRole.ADMIN.value},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["user"]["role"] == UserRole.ADMIN.value


@given(resource_name=resource_names, status=safe_text)
@workflow_settings
def test_generated_resource_create_list_update_delete_workflow(
    client,
    fake_session,
    make_token,
    resource_name: str,
    status: str,
) -> None:
    _reset_fake_session(fake_session)
    workspace, admin = _seed_workspace_user(fake_session)
    token = make_token(
        user_email=admin.email, workspace_id=workspace.id, role=admin.role
    )

    create_response = client.post(
        f"/api/v1/workspaces/{workspace.id}/resources/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": resource_name,
            "type": "database",
            "description": "generated",
            "status": status,
        },
    )
    assert create_response.status_code == 201
    resource_id = create_response.json()["data"]["resource"]["id"]

    list_response = client.get(
        f"/api/v1/workspaces/{workspace.id}/resources/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["data"]["resources"][0]["id"] == resource_id

    update_response = client.patch(
        f"/api/v1/workspaces/{workspace.id}/resources/{resource_id}/",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "updated"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["resource"]["status"] == "updated"

    delete_response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/resources/{resource_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 204
    assert not delete_response.content


@given(
    effect=policy_effects,
    target_role=roles,
    priority=st.integers(min_value=1, max_value=1000),
)
@workflow_settings
def test_generated_policy_and_access_check_workflow(
    client,
    fake_session,
    make_token,
    effect: PolicyEffect,
    target_role: UserRole,
    priority: int,
) -> None:
    _reset_fake_session(fake_session)
    workspace, admin = _seed_workspace_user(fake_session)
    resource = _seed_resource(fake_session, workspace_id=workspace.id)
    token = make_token(
        user_email=admin.email, workspace_id=workspace.id, role=admin.role
    )

    create_policy_response = client.post(
        f"/api/v1/workspaces/{workspace.id}/resources/{resource.id}/policies/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Generated policy",
            "effect": effect.value,
            "target_type": "role",
            "target_value": target_role.value,
            "priority": priority,
        },
    )
    assert create_policy_response.status_code == 201
    policy_id = create_policy_response.json()["data"]["policy"]["id"]

    list_policy_response = client.get(
        f"/api/v1/workspaces/{workspace.id}/resources/{resource.id}/policies/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_policy_response.status_code == 200
    assert list_policy_response.json()["data"]["policies"][0]["id"] == policy_id

    access_response = client.post(
        "/api/v1/access-check/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "workspace_id": str(workspace.id),
            "user_id": str(admin.id),
            "resource_id": str(resource.id),
        },
    )
    assert access_response.status_code == 200
    assert access_response.json()["data"]["access_granted"] is True

    delete_policy_response = client.delete(
        f"/api/v1/workspaces/{workspace.id}/resources/{resource.id}/policies/{policy_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_policy_response.status_code == 204
    assert not delete_policy_response.content


@given(effect=policy_effects)
@small_workflow_settings
def test_generated_non_admin_access_check_follows_effect(
    client,
    fake_session,
    make_token,
    effect: PolicyEffect,
) -> None:
    _reset_fake_session(fake_session)
    workspace, user = _seed_workspace_user(
        fake_session,
        role=UserRole.USER,
        email="member@example.com",
    )
    resource = _seed_resource(fake_session, workspace_id=workspace.id)
    policy = _attach_policy(
        fake_session,
        workspace_id=workspace.id,
        resource_id=resource.id,
        effect=effect,
        target_type="user",
        target_value=str(user.id),
    )
    token = make_token(user_email=user.email, workspace_id=workspace.id, role=user.role)

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
    assert data["access_granted"] is (effect == PolicyEffect.ALLOW)
    assert data["matched_policy_id"] == str(policy.id)

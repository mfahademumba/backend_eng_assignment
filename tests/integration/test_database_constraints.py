from __future__ import annotations

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.models import (
    EffectivePolicy,
    Policy,
    PolicyEffect,
    Resource,
    User,
    UserRole,
    Workspace,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_duplicate_workspace_name_is_rejected(db_session) -> None:
    db_session.add_all([Workspace(name="Acme"), Workspace(name="Acme")])

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_user_email_must_be_unique_per_workspace(db_session) -> None:
    workspace = Workspace(name="Acme")
    db_session.add(workspace)
    await db_session.flush()

    db_session.add_all(
        [
            User(
                workspace_id=workspace.id,
                email="user@example.com",
                full_name="User One",
                password_hash="hashed-password",
                role=UserRole.USER,
            ),
            User(
                workspace_id=workspace.id,
                email="user@example.com",
                full_name="User Two",
                password_hash="hashed-password",
                role=UserRole.USER,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_same_user_email_is_allowed_in_different_workspaces(db_session) -> None:
    workspace_a = Workspace(name="Workspace A")
    workspace_b = Workspace(name="Workspace B")
    db_session.add_all([workspace_a, workspace_b])
    await db_session.flush()

    db_session.add_all(
        [
            User(
                workspace_id=workspace_a.id,
                email="user@example.com",
                full_name="User A",
                password_hash="hashed-password",
                role=UserRole.USER,
            ),
            User(
                workspace_id=workspace_b.id,
                email="user@example.com",
                full_name="User B",
                password_hash="hashed-password",
                role=UserRole.USER,
            ),
        ]
    )

    await db_session.commit()

    user_count = await db_session.scalar(select(func.count()).select_from(User))
    assert user_count == 2


async def test_policy_priority_must_be_positive(db_session) -> None:
    workspace = Workspace(name="Acme")
    db_session.add(workspace)
    await db_session.flush()

    resource = Resource(
        workspace_id=workspace.id,
        name="Customer Database",
        type="database",
        status="active",
    )
    db_session.add(resource)
    await db_session.flush()

    db_session.add(
        Policy(
            workspace_id=workspace.id,
            name="Invalid Policy",
            effect=PolicyEffect.ALLOW,
            target_type="user",
            target_value="user@example.com",
            priority=0,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_effective_policy_cannot_link_policy_to_different_workspace_resource(
    db_session,
) -> None:
    workspace_a = Workspace(name="Workspace A")
    workspace_b = Workspace(name="Workspace B")
    db_session.add_all([workspace_a, workspace_b])
    await db_session.flush()

    resource_a = Resource(
        workspace_id=workspace_a.id,
        name="Workspace A Database",
        type="database",
        status="active",
    )
    resource_b = Resource(
        workspace_id=workspace_b.id,
        name="Workspace B Database",
        type="database",
        status="active",
    )
    db_session.add_all([resource_a, resource_b])
    await db_session.flush()

    policy_a = Policy(
        workspace_id=workspace_a.id,
        name="Workspace A Policy",
        effect=PolicyEffect.ALLOW,
        target_type="user",
        target_value="user@example.com",
        priority=1,
    )
    db_session.add(policy_a)
    await db_session.flush()

    db_session.add(
        EffectivePolicy(
            workspace_id=workspace_a.id,
            resource_id=resource_b.id,
            policy_id=policy_a.id,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_deleting_workspace_cascades_related_records(db_session) -> None:
    workspace = Workspace(name="Acme")
    db_session.add(workspace)
    await db_session.flush()

    user = User(
        workspace_id=workspace.id,
        email="admin@example.com",
        full_name="Admin User",
        password_hash="hashed-password",
        role=UserRole.ADMIN,
    )
    resource = Resource(
        workspace_id=workspace.id,
        name="Customer Database",
        type="database",
        status="active",
    )
    db_session.add_all([user, resource])
    await db_session.flush()

    policy = Policy(
        workspace_id=workspace.id,
        name="Allow Admin",
        effect=PolicyEffect.ALLOW,
        target_type="role",
        target_value="admin",
        priority=1,
    )
    db_session.add(policy)
    await db_session.flush()

    db_session.add(
        EffectivePolicy(
            workspace_id=workspace.id,
            resource_id=resource.id,
            policy_id=policy.id,
        )
    )
    await db_session.commit()

    await db_session.execute(delete(Workspace).where(Workspace.id == workspace.id))
    await db_session.commit()

    for model in (Workspace, User, Resource, Policy, EffectivePolicy):
        count = await db_session.scalar(select(func.count()).select_from(model))
        assert count == 0

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.infrastructure.repositories.resource_repository import ResourceRepository
from app.models import Resource, Workspace


def make_resource(
    *,
    workspace_id,
    name: str,
    resource_type: str = "database",
    status: str = "active",
    created_at: datetime | None = None,
) -> Resource:
    now = created_at or datetime.now(tz=UTC)
    return Resource(
        id=uuid4(),
        workspace_id=workspace_id,
        name=name,
        type=resource_type,
        status=status,
        description=None,
        created_at=now,
        updated_at=now,
    )


def seed_workspace(fake_session, workspace_id, *, name: str) -> None:
    now = datetime.now(tz=UTC)
    fake_session.workspaces[workspace_id] = Workspace(
        id=workspace_id,
        name=name,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_resource_repository_creates_resource(fake_session) -> None:
    workspace_id = uuid4()
    resource = make_resource(workspace_id=workspace_id, name="Production DB")

    repository = ResourceRepository(fake_session)

    result = await repository.create(resource)

    assert result == resource
    assert fake_session.resources[resource.id] == resource


@pytest.mark.anyio
async def test_resource_repository_lists_only_resources_for_workspace_in_stable_order(
    fake_session,
) -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    now = datetime.now(tz=UTC)
    second = make_resource(
        workspace_id=workspace_id,
        name="B Database",
        created_at=now + timedelta(seconds=2),
    )
    first = make_resource(
        workspace_id=workspace_id,
        name="A Database",
        created_at=now + timedelta(seconds=1),
    )
    other_workspace_resource = make_resource(
        workspace_id=other_workspace_id,
        name="Other Database",
        created_at=now,
    )
    fake_session.resources[second.id] = second
    fake_session.resources[first.id] = first
    fake_session.resources[other_workspace_resource.id] = other_workspace_resource

    repository = ResourceRepository(fake_session)

    result = await repository.list_by_workspace_id(workspace_id)

    assert result == [first, second]


@pytest.mark.anyio
async def test_resource_repository_gets_resource_by_workspace_and_resource_id(
    fake_session,
) -> None:
    workspace_id = uuid4()
    resource = make_resource(workspace_id=workspace_id, name="Production DB")
    fake_session.resources[resource.id] = resource

    repository = ResourceRepository(fake_session)

    result = await repository.get_by_workspace_id_and_resource_id(
        workspace_id=workspace_id,
        resource_id=resource.id,
    )

    assert result == resource


@pytest.mark.anyio
async def test_resource_repository_returns_none_for_resource_in_different_workspace(
    fake_session,
) -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    resource = make_resource(
        workspace_id=other_workspace_id,
        name="Other Workspace DB",
    )
    fake_session.resources[resource.id] = resource

    repository = ResourceRepository(fake_session)

    result = await repository.get_by_workspace_id_and_resource_id(
        workspace_id=workspace_id,
        resource_id=resource.id,
    )

    assert result is None


@pytest.mark.anyio
async def test_resource_repository_update_persists_changed_fields(fake_session) -> None:
    workspace_id = uuid4()
    resource = make_resource(workspace_id=workspace_id, name="Production DB")
    fake_session.resources[resource.id] = resource

    repository = ResourceRepository(fake_session)

    resource.name = "Renamed DB"
    resource.status = "inactive"
    result = await repository.update(resource)

    assert result == resource
    assert fake_session.resources[resource.id].name == "Renamed DB"
    assert fake_session.resources[resource.id].status == "inactive"


@pytest.mark.anyio
async def test_resource_repository_deletes_resource_by_workspace_and_resource_id(
    fake_session,
) -> None:
    workspace_id = uuid4()
    resource = make_resource(workspace_id=workspace_id, name="Production DB")
    fake_session.resources[resource.id] = resource

    repository = ResourceRepository(fake_session)

    await repository.delete_by_workspace_id_and_resource_id(
        workspace_id=workspace_id,
        resource_id=resource.id,
    )

    assert resource.id not in fake_session.resources


@pytest.mark.anyio
async def test_resource_repository_does_not_delete_resource_from_different_workspace(
    fake_session,
) -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    seed_workspace(fake_session, workspace_id, name="Workspace A")
    seed_workspace(fake_session, other_workspace_id, name="Workspace B")
    resource = make_resource(
        workspace_id=other_workspace_id,
        name="Other Workspace DB",
    )
    fake_session.resources[resource.id] = resource

    repository = ResourceRepository(fake_session)

    await repository.delete_by_workspace_id_and_resource_id(
        workspace_id=workspace_id,
        resource_id=resource.id,
    )

    assert fake_session.resources[resource.id] == resource

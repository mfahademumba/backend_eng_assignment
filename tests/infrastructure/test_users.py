from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.infrastructure.repositories.user_repository import UserRepository
from app.models import User, UserRole


def make_user(
    *,
    workspace_id,
    email: str,
    role: UserRole = UserRole.USER,
    token_version: int = 0,
    created_at: datetime | None = None,
) -> User:
    now = created_at or datetime.now(tz=UTC)
    return User(
        id=uuid4(),
        workspace_id=workspace_id,
        email=email,
        full_name="Test User",
        password_hash="hashed-password",
        role=role,
        token_version=token_version,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_user_repository_gets_user_by_workspace_and_email(fake_session) -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    user = make_user(workspace_id=workspace_id, email="user@acme.com")
    same_email_other_workspace = make_user(
        workspace_id=other_workspace_id,
        email="user@acme.com",
    )
    fake_session.users[(workspace_id, user.email)] = user
    fake_session.users[
        (
            other_workspace_id,
            same_email_other_workspace.email,
        )
    ] = same_email_other_workspace

    repository = UserRepository(fake_session)

    result = await repository.get_by_workspace_id_and_email(
        workspace_id=workspace_id,
        email="user@acme.com",
    )

    assert result == user


@pytest.mark.anyio
async def test_user_repository_returns_none_for_email_in_different_workspace(
    fake_session,
) -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    user = make_user(workspace_id=other_workspace_id, email="user@acme.com")
    fake_session.users[(other_workspace_id, user.email)] = user

    repository = UserRepository(fake_session)

    result = await repository.get_by_workspace_id_and_email(
        workspace_id=workspace_id,
        email="user@acme.com",
    )

    assert result is None


@pytest.mark.anyio
async def test_user_repository_lists_only_users_for_workspace_in_stable_order(
    fake_session,
) -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    now = datetime.now(tz=UTC)
    second = make_user(
        workspace_id=workspace_id,
        email="second@acme.com",
        created_at=now + timedelta(seconds=2),
    )
    first = make_user(
        workspace_id=workspace_id,
        email="first@acme.com",
        created_at=now + timedelta(seconds=1),
    )
    other_workspace_user = make_user(
        workspace_id=other_workspace_id,
        email="other@acme.com",
        created_at=now,
    )
    fake_session.users[(workspace_id, second.email)] = second
    fake_session.users[(workspace_id, first.email)] = first
    fake_session.users[(other_workspace_id, other_workspace_user.email)] = (
        other_workspace_user
    )

    repository = UserRepository(fake_session)

    result = await repository.list_by_workspace_id(workspace_id)

    assert result == [first, second]


@pytest.mark.anyio
async def test_user_repository_gets_user_by_workspace_and_user_id(fake_session) -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    user = make_user(workspace_id=workspace_id, email="user@acme.com")
    wrong_workspace_user = make_user(
        workspace_id=other_workspace_id,
        email="other@acme.com",
    )
    fake_session.users[(workspace_id, user.email)] = user
    fake_session.users[(other_workspace_id, wrong_workspace_user.email)] = (
        wrong_workspace_user
    )

    repository = UserRepository(fake_session)

    result = await repository.get_by_workspace_id_and_user_id(
        workspace_id=workspace_id,
        user_id=user.id,
    )

    assert result == user


@pytest.mark.anyio
async def test_user_repository_returns_none_for_user_id_in_different_workspace(
    fake_session,
) -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    user = make_user(workspace_id=other_workspace_id, email="user@other.com")
    fake_session.users[(other_workspace_id, user.email)] = user

    repository = UserRepository(fake_session)

    result = await repository.get_by_workspace_id_and_user_id(
        workspace_id=workspace_id,
        user_id=user.id,
    )

    assert result is None


@pytest.mark.anyio
async def test_user_repository_update_role_persists_changed_role(fake_session) -> None:
    workspace_id = uuid4()
    user = make_user(workspace_id=workspace_id, email="user@acme.com")
    fake_session.users[(workspace_id, user.email)] = user

    repository = UserRepository(fake_session)

    user.role = UserRole.ADMIN
    result = await repository.update_role(user)

    assert result == user
    assert fake_session.users[(workspace_id, user.email)].role == UserRole.ADMIN


@pytest.mark.anyio
async def test_user_repository_increment_token_version(fake_session) -> None:
    workspace_id = uuid4()
    user = make_user(
        workspace_id=workspace_id,
        email="user@acme.com",
        token_version=3,
    )
    fake_session.users[(workspace_id, user.email)] = user

    repository = UserRepository(fake_session)

    result = await repository.increment_token_version(user)

    assert result == user
    assert user.token_version == 4

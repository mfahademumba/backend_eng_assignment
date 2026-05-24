from __future__ import annotations

import sys
from collections.abc import AsyncIterator, Generator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class FakeScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def all(self) -> list[Any]:
        return self.values


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added_objects: list[Any] = []
        self.workspaces: dict[UUID, Any] = {}
        self.users: dict[tuple[UUID, str], Any] = {}
        self.resources: dict[UUID, Any] = {}
        self.policies: dict[UUID, Any] = {}
        self.effective_policies: dict[UUID, Any] = {}
        self.scalar_result: Any | None = None

    def add_all(self, objects: list[Any]) -> None:
        self.added_objects.extend(objects)

    async def flush(self) -> None:
        self._assign_defaults()

    def _assign_defaults(self) -> None:
        now = datetime.now(tz=UTC)
        for obj in self.added_objects:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            if getattr(obj, "updated_at", None) is None:
                obj.updated_at = now
            if (
                obj.__class__.__name__ == "User"
                and getattr(obj, "workspace_id", None) is None
                and getattr(obj, "workspace", None) is not None
            ):
                obj.workspace_id = obj.workspace.id

    async def commit(self) -> None:
        self._assign_defaults()

        for obj in self.added_objects:
            if obj.__class__.__name__ == "Workspace":
                self.workspaces[obj.id] = obj
            elif obj.__class__.__name__ == "User":
                self.users[(obj.workspace_id, obj.email)] = obj
            elif obj.__class__.__name__ == "Resource":
                self.resources[obj.id] = obj
            elif obj.__class__.__name__ == "Policy":
                self.policies[obj.id] = obj
            elif obj.__class__.__name__ == "EffectivePolicy":
                obj.policy = self.policies.get(obj.policy_id)
                obj.resource = self.resources.get(obj.resource_id)
                self.effective_policies[obj.id] = obj
        self.added_objects = []

    async def rollback(self) -> None:
        return None

    async def refresh(self, _obj: Any) -> None:
        return None

    async def get(self, model: Any, primary_key: Any) -> Any | None:
        if getattr(model, "__name__", None) == "Workspace":
            return self.workspaces.get(primary_key)
        if getattr(model, "__name__", None) == "User":
            for user in self.users.values():
                if getattr(user, "id", None) == primary_key:
                    return user
        if getattr(model, "__name__", None) == "Resource":
            return self.resources.get(primary_key)
        if getattr(model, "__name__", None) == "Policy":
            return self.policies.get(primary_key)
        if getattr(model, "__name__", None) == "EffectivePolicy":
            return self.effective_policies.get(primary_key)
        return None

    async def scalar(self, statement: Any) -> Any | None:
        entity = None
        column_descriptions = getattr(statement, "column_descriptions", [])
        if column_descriptions:
            entity = column_descriptions[0].get("entity")
        entity_name = getattr(entity, "__name__", None)
        if self.scalar_result is not None and entity_name == "User":
            return self.scalar_result

        params = getattr(statement.compile(), "params", {})
        workspace_id = params.get("workspace_id_1")
        email = params.get("email_1")
        if workspace_id is not None and email is not None:
            return self.users.get((workspace_id, email))

        policy_id = params.get("id_1")
        resource_id = params.get("resource_id_1")
        if (
            policy_id is not None
            and workspace_id is not None
            and resource_id is not None
        ):
            for effective_policy in self.effective_policies.values():
                if (
                    effective_policy.workspace_id == workspace_id
                    and effective_policy.resource_id == resource_id
                    and effective_policy.policy_id == policy_id
                ):
                    return self.policies.get(policy_id)

        return None

    async def scalars(self, statement: Any) -> FakeScalarResult:
        entity = None
        column_descriptions = getattr(statement, "column_descriptions", [])
        if column_descriptions:
            entity = column_descriptions[0].get("entity")
        entity_name = getattr(entity, "__name__", None)
        params = getattr(statement.compile(), "params", {})
        workspace_id = params.get("workspace_id_1")
        resource_id = params.get("resource_id_1")

        if entity_name == "Policy":
            policies = [
                self.policies[effective_policy.policy_id]
                for effective_policy in self.effective_policies.values()
                if effective_policy.workspace_id == workspace_id
                and effective_policy.resource_id == resource_id
                and effective_policy.policy_id in self.policies
            ]
            policies.sort(
                key=lambda policy: (-policy.priority, policy.created_at, str(policy.id))
            )
            return FakeScalarResult(policies)

        if entity_name == "EffectivePolicy":
            effective_policies = [
                effective_policy
                for effective_policy in self.effective_policies.values()
                if effective_policy.workspace_id == workspace_id
                and effective_policy.resource_id == resource_id
            ]
            for effective_policy in effective_policies:
                effective_policy.policy = self.policies.get(effective_policy.policy_id)
            effective_policies.sort(
                key=lambda effective_policy: (
                    -effective_policy.policy.priority,
                    effective_policy.policy.created_at,
                    str(effective_policy.policy.id),
                )
            )
            return FakeScalarResult(effective_policies)

        users = [
            user
            for (user_workspace_id, _email), user in self.users.items()
            if workspace_id is None or user_workspace_id == workspace_id
        ]
        users.sort(key=lambda user: (user.created_at, user.email))
        return FakeScalarResult(users)

    async def execute(self, statement: Any) -> None:
        params = getattr(statement.compile(), "params", {})
        workspace_ids = [
            value
            for value in params.values()
            if any(workspace.id == value for workspace in self.workspaces.values())
        ]
        resource_ids = [value for value in params.values() if value in self.resources]
        workspace_id = workspace_ids[0] if workspace_ids else None
        resource_id = resource_ids[0] if resource_ids else None
        policy_ids = [value for value in params.values() if value in self.policies]
        if not policy_ids:
            policy_ids = list(self.policies)
        for policy_id in policy_ids:
            policy = self.policies.get(policy_id)
            if policy is None or (
                workspace_id is not None and policy.workspace_id != workspace_id
            ):
                continue
            matching_effective_policies = [
                (effective_policy_id, effective_policy)
                for effective_policy_id, effective_policy in self.effective_policies.items()
                if effective_policy.policy_id == policy_id
                and (resource_id is None or effective_policy.resource_id == resource_id)
            ]
            if not matching_effective_policies:
                continue
            self.policies.pop(policy_id, None)
            for effective_policy_id, _effective_policy in matching_effective_policies:
                self.effective_policies.pop(effective_policy_id, None)
        return None


@pytest.fixture()
def fake_session() -> FakeAsyncSession:
    return FakeAsyncSession()


@pytest.fixture()
def client(fake_session: FakeAsyncSession) -> Generator[TestClient, None, None]:
    async def override_get_db_session() -> AsyncIterator[FakeAsyncSession]:
        yield fake_session

    from app.infrastructure.database import get_db_session
    from main import app

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def client_no_raise(
    fake_session: FakeAsyncSession,
) -> Generator[TestClient, None, None]:
    async def override_get_db_session() -> AsyncIterator[FakeAsyncSession]:
        yield fake_session

    from app.infrastructure.database import get_db_session
    from main import app

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "test-secret-key-test-secret-key-1234567890"

    from app import auth as auth_module

    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: SimpleNamespace(
            jwt_secret_key=SecretStr(secret),
            jwt_algorithm="HS256",
        ),
    )
    return secret


@pytest.fixture()
def make_token(auth_secret: str):
    def _make_token(
        *,
        user_email: str,
        workspace_id: UUID,
        role: Any,
        token_version: int = 0,
        token_type: str = "access",
    ) -> str:
        payload = {
            "user_email": user_email,
            "workspace_id": str(workspace_id),
            "role": role.value,
            "token_version": token_version,
            "type": token_type,
        }
        return jwt.encode(payload, auth_secret, algorithm="HS256")

    return _make_token

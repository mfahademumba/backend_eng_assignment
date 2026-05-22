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


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added_objects: list[Any] = []
        self.workspaces: dict[UUID, Any] = {}
        self.users: dict[tuple[UUID, str], Any] = {}
        self.scalar_result: Any | None = None

    def add_all(self, objects: list[Any]) -> None:
        self.added_objects.extend(objects)

    async def commit(self) -> None:
        now = datetime.now(tz=UTC)

        for obj in self.added_objects:
            if obj.__class__.__name__ == "Workspace":
                if getattr(obj, "id", None) is None:
                    obj.id = uuid4()
                if getattr(obj, "created_at", None) is None:
                    obj.created_at = now
                if getattr(obj, "updated_at", None) is None:
                    obj.updated_at = now

        for obj in self.added_objects:
            if obj.__class__.__name__ == "User":
                if (
                    getattr(obj, "workspace_id", None) is None
                    and getattr(obj, "workspace", None) is not None
                ):
                    obj.workspace_id = obj.workspace.id
                if getattr(obj, "id", None) is None:
                    obj.id = uuid4()
                if getattr(obj, "created_at", None) is None:
                    obj.created_at = now
                if getattr(obj, "updated_at", None) is None:
                    obj.updated_at = now

        for obj in self.added_objects:
            if obj.__class__.__name__ == "Workspace":
                self.workspaces[obj.id] = obj
            elif obj.__class__.__name__ == "User":
                self.users[(obj.workspace_id, obj.email)] = obj

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
        return None

    async def scalar(self, _statement: Any) -> Any | None:
        return self.scalar_result


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
    ) -> str:
        payload = {
            "user_email": user_email,
            "workspace_id": str(workspace_id),
            "role": role.value,
            "token_version": token_version,
        }
        return jwt.encode(payload, auth_secret, algorithm="HS256")

    return _make_token

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.api.v1.workspaces import get_workspace_service
from app.models import User, UserRole, Workspace
from main import app


def test_create_workspace_returns_workspace_and_admin_credentials(
    client,
    fake_session,
) -> None:
    response = client.post(
        "/api/v1/workspaces/",
        json={
            "name": "Acme Corp",
            "admin_email": "admin@acme.com",
            "admin_password": "SecurePass123!",
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Workspace created successfully."

    data = body["data"]
    assert data["workspace"]["name"] == "Acme Corp"
    assert data["workspace"]["id"]
    assert data["admin_credentials"]["email"] == "admin@acme.com"
    assert data["admin_credentials"]["role"] == "admin"
    assert "admin_password" not in data

    admin_user = fake_session.users[(UUID(data["workspace"]["id"]), "admin@acme.com")]
    assert admin_user.password_hash != "SecurePass123!"
    assert admin_user.password_hash.startswith("argon2$")


def test_create_workspace_rejects_weak_password(client) -> None:
    response = client.post(
        "/api/v1/workspaces/",
        json={
            "name": "Acme Corp",
            "admin_email": "admin@acme.com",
            "admin_password": "weakpass1",
        },
    )

    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Validation failed."
    assert body["data"] is None
    assert any(
        error["field"] == "body.admin_password" and error["code"] == "validation_error"
        for error in body["errors"]
    )


def test_create_workspace_returns_normalized_500_for_unexpected_errors(
    client_no_raise,
) -> None:
    class FailingWorkspaceService:
        async def create_workspace(self, _payload):
            raise RuntimeError("database is unavailable")

    app.dependency_overrides[get_workspace_service] = lambda: FailingWorkspaceService()
    try:
        response = client_no_raise.post(
            "/api/v1/workspaces/",
            json={
                "name": "Acme Corp",
                "admin_email": "admin@acme.com",
                "admin_password": "SecurePass123!",
            },
        )
    finally:
        app.dependency_overrides.pop(get_workspace_service, None)

    assert response.status_code == 500

    body = response.json()
    assert body == {
        "success": False,
        "message": "Internal server error.",
        "data": None,
        "errors": [
            {
                "code": "internal_server_error",
                "detail": "Internal server error.",
                "field": None,
            }
        ],
    }


def test_create_workspace_openapi_documents_payload_error_responses(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    responses = response.json()["paths"]["/api/v1/workspaces/"]["post"]["responses"]
    assert "400" in responses
    assert "422" in responses


def test_get_workspace_details_returns_200_for_admin(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_id = uuid4()
    user_email = "admin@acme.com"
    now = datetime.now(tz=UTC)

    workspace = Workspace(
        id=workspace_id,
        name="Acme Corp",
        created_at=now,
        updated_at=now,
    )
    admin_user = User(
        id=uuid4(),
        workspace_id=workspace_id,
        email=user_email,
        password_hash="hashed-password",
        role=UserRole.ADMIN,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.workspaces[workspace_id] = workspace
    fake_session.scalar_result = admin_user

    token = make_token(
        user_email=user_email,
        workspace_id=workspace_id,
        role=UserRole.ADMIN,
    )

    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Workspace retrieved successfully."
    assert body["data"]["workspace"]["id"] == str(workspace_id)
    assert body["data"]["workspace"]["name"] == "Acme Corp"


def test_get_workspace_details_returns_403_for_non_admin_user(
    client,
    fake_session,
    make_token,
) -> None:
    workspace_id = uuid4()
    user_email = "member@acme.com"
    now = datetime.now(tz=UTC)

    workspace = Workspace(
        id=workspace_id,
        name="Acme Corp",
        created_at=now,
        updated_at=now,
    )
    regular_user = User(
        id=uuid4(),
        workspace_id=workspace_id,
        email=user_email,
        password_hash="hashed-password",
        role=UserRole.USER,
        token_version=0,
        created_at=now,
        updated_at=now,
    )
    fake_session.workspaces[workspace_id] = workspace
    fake_session.scalar_result = regular_user

    token = make_token(
        user_email=user_email,
        workspace_id=workspace_id,
        role=UserRole.USER,
    )

    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403

    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Admin access is required."

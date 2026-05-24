from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from hypothesis import given
from hypothesis import strategies as st
from pydantic import SecretStr

from app import auth as auth_module
from app.auth import (
    AuthenticatedUser,
    create_token_pair,
    decode_access_token,
    decode_refresh_token,
)
from app.models import UserRole

SECRET = "test-secret-key-test-secret-key-1234567890"


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_module,
        "get_settings",
        lambda: SimpleNamespace(
            jwt_secret_key=SecretStr(SECRET),
            jwt_algorithm="HS256",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        ),
    )


valid_emails = st.emails().filter(lambda email: len(email) <= 255)
roles = st.sampled_from(list(UserRole))
token_versions = st.integers(min_value=0, max_value=1_000_000)


def _signed_payload(*, token_type: str, role: UserRole, token_version: int) -> str:
    payload = {
        "user_email": "user@example.com",
        "workspace_id": str(uuid4()),
        "role": role.value,
        "token_version": token_version,
        "type": token_type,
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


@given(email=valid_emails, role=roles, token_version=token_versions)
def test_created_access_and_refresh_tokens_decode_to_original_user_payload(
    email: str, role: UserRole, token_version: int
) -> None:
    workspace_id = uuid4()
    user = AuthenticatedUser(
        id=uuid4(),
        email=email,
        workspace_id=workspace_id,
        role=role,
        token_version=token_version,
    )

    token_pair = create_token_pair(user)

    access_payload = decode_access_token(token_pair.access_token)
    assert access_payload.user_email == user.email
    assert access_payload.workspace_id == workspace_id
    assert access_payload.role == role
    assert access_payload.token_version == token_version
    assert access_payload.type == "access"

    refresh_payload = decode_refresh_token(token_pair.refresh_token)
    assert refresh_payload.user_email == user.email
    assert refresh_payload.workspace_id == workspace_id
    assert refresh_payload.role == role
    assert refresh_payload.token_version == token_version
    assert refresh_payload.type == "refresh"


@given(token=st.text(min_size=1).filter(lambda value: value.count(".") != 2))
def test_malformed_tokens_are_rejected_without_leaking_decode_errors(
    token: str,
) -> None:
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Access token is invalid."


@given(role=roles, token_version=token_versions)
def test_access_decoder_rejects_refresh_tokens(
    role: UserRole, token_version: int
) -> None:
    token = _signed_payload(
        token_type="refresh",
        role=role,
        token_version=token_version,
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Access token is invalid."


@given(role=roles, token_version=token_versions)
def test_refresh_decoder_rejects_access_tokens(
    role: UserRole, token_version: int
) -> None:
    token = _signed_payload(
        token_type="access",
        role=role,
        token_version=token_version,
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_refresh_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Refresh token is invalid."


@given(
    token_type=st.text().filter(lambda value: value not in {"access", "refresh"}),
    role=roles,
    token_version=token_versions,
)
def test_tokens_with_unknown_type_are_rejected_as_invalid_payloads(
    token_type: str, role: UserRole, token_version: int
) -> None:
    token = _signed_payload(
        token_type=token_type,
        role=role,
        token_version=token_version,
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Access token payload is invalid."

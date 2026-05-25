from __future__ import annotations

import string
import uuid
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.models import PolicyEffect, UserRole
from app.schemas.policy import PolicyCreateRequest
from app.schemas.resource import ResourceUpdateRequest
from app.schemas.user import WorkspaceUserCreateRequest

valid_schema_text = st.text(
    alphabet=string.ascii_letters + string.digits + " _-",
    min_size=1,
    max_size=255,
)

strong_passwords = st.builds(
    lambda prefix, upper, lower, digit, suffix: (
        f"{prefix}{upper}{lower}{digit}{suffix}"
    ),
    st.text(alphabet=string.printable.strip(), max_size=20),
    st.sampled_from(string.ascii_uppercase),
    st.sampled_from(string.ascii_lowercase),
    st.sampled_from(string.digits),
    st.text(alphabet=string.printable.strip(), max_size=20),
).filter(lambda value: 8 <= len(value) <= 128)


@given(
    name=valid_schema_text,
    effect=st.sampled_from(list(PolicyEffect)),
    role=st.sampled_from(list(UserRole)),
    priority=st.integers(min_value=1, max_value=10_000),
)
def test_role_policy_create_requests_accept_valid_role_targets(
    name: str,
    effect: PolicyEffect,
    role: UserRole,
    priority: int,
) -> None:
    request = PolicyCreateRequest(
        name=name,
        effect=effect,
        target_type="role",
        target_value=role.value,
        priority=priority,
    )

    assert request.target_type == "role"
    assert request.target_value == role.value
    assert request.priority == priority


@given(
    name=valid_schema_text,
    effect=st.sampled_from(list(PolicyEffect)),
    user_id=st.uuids(),
    priority=st.integers(min_value=1, max_value=10_000),
)
def test_user_policy_create_requests_accept_valid_uuid_targets(
    name: str,
    effect: PolicyEffect,
    user_id: uuid.UUID,
    priority: int,
) -> None:
    request = PolicyCreateRequest(
        name=name,
        effect=effect,
        target_type="user",
        target_value=str(user_id),
        priority=priority,
    )

    assert request.target_type == "user"
    assert request.target_value == str(user_id)


@given(priority=st.integers(max_value=0))
def test_policy_priorities_must_be_greater_than_zero(priority: int) -> None:
    with pytest.raises(ValidationError):
        PolicyCreateRequest(
            name="Policy",
            effect=PolicyEffect.ALLOW,
            target_type="role",
            target_value=UserRole.USER.value,
            priority=priority,
        )


@given(
    target_value=st.text(min_size=1).filter(
        lambda value: value not in {role.value for role in UserRole}
    )
)
def test_role_policy_target_value_must_be_valid_user_role(target_value: str) -> None:
    with pytest.raises(ValidationError):
        PolicyCreateRequest(
            name="Policy",
            effect=PolicyEffect.ALLOW,
            target_type="role",
            target_value=target_value,
            priority=1,
        )


@given(target_value=st.text(min_size=1).filter(lambda value: not _is_uuid(value)))
def test_user_policy_target_value_must_be_valid_uuid(target_value: str) -> None:
    with pytest.raises(ValidationError):
        PolicyCreateRequest(
            name="Policy",
            effect=PolicyEffect.ALLOW,
            target_type="user",
            target_value=target_value,
            priority=1,
        )


@given(
    name=st.one_of(st.none(), valid_schema_text),
    resource_type=st.one_of(st.none(), valid_schema_text),
    description=st.one_of(st.none(), st.text(max_size=5000)),
    status=st.one_of(st.none(), valid_schema_text),
)
def test_resource_update_requests_support_partial_updates(
    name: str | None,
    resource_type: str | None,
    description: str | None,
    status: str | None,
) -> None:
    request = ResourceUpdateRequest(
        name=name,
        type=resource_type,
        description=description,
        status=status,
    )

    assert request.model_dump(exclude_unset=True) == {
        "name": name,
        "type": resource_type,
        "description": description,
        "status": status,
    }


@given(
    email=st.emails(),
    password=strong_passwords,
    full_name=valid_schema_text,
)
def test_workspace_user_create_defaults_to_user_role(
    email: str,
    password: str,
    full_name: str,
) -> None:
    request = WorkspaceUserCreateRequest(
        email=email,
        password=password,
        full_name=full_name,
    )

    assert request.email
    assert request.password == password
    assert request.full_name == full_name
    assert request.role == UserRole.USER


@given(
    role=st.text(min_size=1).filter(
        lambda value: value not in {role.value for role in UserRole}
    )
)
def test_workspace_user_role_must_be_valid_user_role(role: Any) -> None:
    with pytest.raises(ValidationError):
        WorkspaceUserCreateRequest(
            email="user@example.com",
            password="StrongPass1",
            role=role,
            full_name="User Name",
        )


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True

from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.models import PolicyEffect, User, UserRole
from app.policy_engine import admin_bypass_result, policy_eval


def _user(*, role: UserRole = UserRole.USER, user_id: UUID | None = None) -> User:
    return User(
        id=user_id or uuid4(),
        workspace_id=uuid4(),
        email="user@example.com",
        full_name="User",
        password_hash="hashed-password",
        role=role,
        token_version=0,
    )


def _effective_policy(
    *,
    effect: PolicyEffect,
    target_type: str,
    target_value: str,
    priority: int,
):
    policy = SimpleNamespace(
        id=uuid4(),
        name=f"{effect.value}-{target_type}-{priority}",
        effect=effect,
        target_type=target_type,
        target_value=target_value,
        priority=priority,
    )
    return SimpleNamespace(policy=policy)


policy_effects = st.sampled_from(list(PolicyEffect))
user_roles = st.sampled_from(list(UserRole))
positive_priorities = st.integers(min_value=1, max_value=1_000_000)


@given(effect=policy_effects, role=user_roles, priority=positive_priorities)
def test_role_policy_matching_result_follows_policy_effect(
    effect: PolicyEffect, role: UserRole, priority: int
) -> None:
    user = _user(role=role)
    effective_policy = _effective_policy(
        effect=effect,
        target_type="role",
        target_value=role.value,
        priority=priority,
    )

    result = policy_eval([effective_policy], user)

    assert result.access_granted is (effect == PolicyEffect.ALLOW)
    assert result.matched_policy_id == effective_policy.policy.id
    assert result.reason == (
        f"Matched policy: {effective_policy.policy.name} (priority {priority})"
    )


@given(effect=policy_effects, priority=positive_priorities)
def test_user_policy_matching_result_follows_policy_effect(
    effect: PolicyEffect, priority: int
) -> None:
    user_id = uuid4()
    user = _user(user_id=user_id)
    effective_policy = _effective_policy(
        effect=effect,
        target_type="user",
        target_value=str(user_id),
        priority=priority,
    )

    result = policy_eval([effective_policy], user)

    assert result.access_granted is (effect == PolicyEffect.ALLOW)
    assert result.matched_policy_id == effective_policy.policy.id


@given(
    target_type=st.text().filter(lambda value: value not in {"role", "user"}),
    target_value=st.text(),
    effect=policy_effects,
    priority=positive_priorities,
)
def test_unknown_policy_target_types_never_match(
    target_type: str, target_value: str, effect: PolicyEffect, priority: int
) -> None:
    user = _user()
    effective_policy = _effective_policy(
        effect=effect,
        target_type=target_type,
        target_value=target_value,
        priority=priority,
    )

    result = policy_eval([effective_policy], user)

    assert result.access_granted is False
    assert result.matched_policy_id is None
    assert result.reason == "No matching policy found. Access denied by default."


@given(first_effect=policy_effects, second_effect=policy_effects)
def test_policy_eval_uses_first_matching_effective_policy(
    first_effect: PolicyEffect, second_effect: PolicyEffect
) -> None:
    user = _user(role=UserRole.USER)
    first_policy = _effective_policy(
        effect=first_effect,
        target_type="role",
        target_value="user",
        priority=20,
    )
    second_policy = _effective_policy(
        effect=second_effect,
        target_type="role",
        target_value="user",
        priority=10,
    )

    result = policy_eval([first_policy, second_policy], user)

    assert result.access_granted is (first_effect == PolicyEffect.ALLOW)
    assert result.matched_policy_id == first_policy.policy.id


@given(role=user_roles)
def test_admin_bypass_is_restricted_to_admin_users(role: UserRole) -> None:
    user = _user(role=role)

    if role == UserRole.ADMIN:
        result = admin_bypass_result(user)
        assert result.access_granted is True
        assert result.matched_policy_id is None
    else:
        with pytest.raises(ValueError, match="Admin bypass can only be used"):
            admin_bypass_result(user)

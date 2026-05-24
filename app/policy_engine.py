from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.models import PolicyEffect, User, UserRole


@dataclass(frozen=True)
class PolicyEvaluationResult:
    access_granted: bool
    reason: str
    matched_policy_id: uuid.UUID | None = None


def _policy_matches_user(policy, user: User) -> bool:
    if policy.target_type == "role":
        return policy.target_value == user.role.value

    if policy.target_type == "user":
        return policy.target_value == str(user.id)

    return False


def policy_eval(sorted_effective_policies: list, user: User) -> PolicyEvaluationResult:
    for effective_policy in sorted_effective_policies:
        policy = effective_policy.policy
        if not _policy_matches_user(policy, user):
            continue

        access_granted = policy.effect == PolicyEffect.ALLOW
        return PolicyEvaluationResult(
            access_granted=access_granted,
            reason=f"Matched policy: {policy.name} (priority {policy.priority})",
            matched_policy_id=policy.id,
        )

    return PolicyEvaluationResult(
        access_granted=False,
        reason="No matching policy found. Access denied by default.",
        matched_policy_id=None,
    )


def admin_bypass_result(user: User) -> PolicyEvaluationResult:
    if user.role != UserRole.ADMIN:
        raise ValueError("Admin bypass can only be used for admin users.")

    return PolicyEvaluationResult(
        access_granted=True,
        reason="Admin bypass: admins always have access to resources in their workspace",
        matched_policy_id=None,
    )

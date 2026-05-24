from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.models import PolicyEffect, UserRole

PolicyName = Annotated[str, StringConstraints(min_length=1, max_length=255)]
TargetType = Literal["role", "user"]


class PolicyCreateRequest(BaseModel):
    name: PolicyName
    effect: PolicyEffect
    target_type: TargetType
    target_value: str
    priority: int

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Priority must be greater than 0.")
        return value

    @field_validator("target_value")
    @classmethod
    def validate_target_value(cls, value: str, info) -> str:
        target_type = info.data.get("target_type")
        if target_type == "role":
            allowed_roles = {role.value for role in UserRole}
            if value not in allowed_roles:
                raise ValueError("Role target_value must be a valid user role.")
        elif target_type == "user":
            try:
                uuid.UUID(value)
            except ValueError as exc:
                raise ValueError("User target_value must be a valid UUID.") from exc
        return value


class PolicySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    effect: PolicyEffect
    target_type: str
    target_value: str
    priority: int
    created_at: datetime
    updated_at: datetime


class PolicyCreateData(BaseModel):
    policy: PolicySummary


class PolicyListData(BaseModel):
    policies: list[PolicySummary]


class PolicyDeleteData(BaseModel):
    policy_id: uuid.UUID

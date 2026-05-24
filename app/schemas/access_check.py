from __future__ import annotations

import uuid

from pydantic import BaseModel


class AccessCheckRequest(BaseModel):
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    resource_id: uuid.UUID


class AccessCheckData(BaseModel):
    access_granted: bool
    reason: str
    matched_policy_id: uuid.UUID | None = None

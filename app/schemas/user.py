from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from app.models import UserRole
from app.schemas.validators import StrongPassword

FullName = Annotated[
    str,
    StringConstraints(min_length=1, max_length=255),
]


class WorkspaceUserCreateRequest(BaseModel):
    email: EmailStr
    password: StrongPassword
    role: UserRole = UserRole.USER
    full_name: FullName


class WorkspaceUserUpdateRoleRequest(BaseModel):
    role: UserRole


class WorkspaceUserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    created_at: datetime
    updated_at: datetime


class WorkspaceUserCreateData(BaseModel):
    user: WorkspaceUserSummary


class WorkspaceUserListData(BaseModel):
    users: list[WorkspaceUserSummary]


class WorkspaceUserUpdateData(BaseModel):
    user: WorkspaceUserSummary

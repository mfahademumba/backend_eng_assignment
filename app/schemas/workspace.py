from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from app.models import UserRole
from app.schemas.validators import StrongPassword

WorkspaceName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=255),
]
PasswordValue = StrongPassword


class WorkspaceCreateRequest(BaseModel):
    name: WorkspaceName
    admin_email: EmailStr
    admin_password: PasswordValue


class WorkspaceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime


class WorkspaceAdminCredentials(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    role: UserRole


class WorkspaceCreateData(BaseModel):
    workspace: WorkspaceSummary
    admin_credentials: WorkspaceAdminCredentials


class WorkspaceDetailsData(BaseModel):
    workspace: WorkspaceSummary

from __future__ import annotations

import uuid
from typing import Annotated

from pydantic import BaseModel, EmailStr, StringConstraints

from app.auth import TokenPair


class LoginRequest(BaseModel):
    workspace_id: uuid.UUID
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=1)]


class LoginData(TokenPair):
    pass


class RefreshRequest(BaseModel):
    refresh_token: Annotated[str, StringConstraints(min_length=1)]


class RefreshData(TokenPair):
    pass


class LogoutData(BaseModel):
    token_version: int

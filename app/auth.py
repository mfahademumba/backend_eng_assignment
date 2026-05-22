from __future__ import annotations

import base64
import hashlib
import importlib
import os
import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from pydantic import BaseModel, ConfigDict, EmailStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db_session
from app.infrastructure.repositories.user_repository import UserRepository
from app.models import UserRole
from config.settings import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    user_email: EmailStr
    workspace_id: uuid.UUID
    role: UserRole
    token_version: int


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    workspace_id: uuid.UUID
    role: UserRole
    token_version: int


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")

    try:
        bcrypt = importlib.import_module("bcrypt")
    except ModuleNotFoundError:
        salt = os.urandom(16)
        password_hash = hashlib.scrypt(password_bytes, salt=salt, n=16384, r=8, p=1)
        encoded_salt = base64.b64encode(salt).decode("utf-8")
        encoded_hash = base64.b64encode(password_hash).decode("utf-8")
        return f"scrypt${encoded_salt}${encoded_hash}"

    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return f"bcrypt${hashed_password.decode('utf-8')}"


def decode_access_token(token: str) -> TokenPayload:
    settings = get_settings()
    secret = (
        settings.jwt_secret_key.get_secret_value()
        if settings.jwt_secret_key is not None
        else None
    )
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET_KEY is not configured.",
        )

    try:
        payload = jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired.",
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is invalid.",
        ) from exc

    try:
        return TokenPayload.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token payload is invalid.",
        ) from exc


async def get_current_admin_for_workspace(
    workspace_id: uuid.UUID,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
        )

    token_payload = decode_access_token(credentials.credentials)
    if token_payload.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace.",
        )

    user_repository = UserRepository(session)
    user = await user_repository.get_by_workspace_id_and_email(
        workspace_id=token_payload.workspace_id,
        email=token_payload.user_email,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user was not found.",
        )

    if user.token_version != token_payload.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is no longer valid.",
        )

    if user.role != UserRole.ADMIN or token_payload.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        )

    return AuthenticatedUser.model_validate(user)

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

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


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


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


def verify_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode("utf-8")

    if password_hash.startswith("bcrypt$"):
        try:
            bcrypt = importlib.import_module("bcrypt")
        except ModuleNotFoundError:
            return False
        stored_hash = password_hash.removeprefix("bcrypt$").encode("utf-8")
        return bool(bcrypt.checkpw(password_bytes, stored_hash))

    if password_hash.startswith("scrypt$"):
        try:
            _prefix, encoded_salt, encoded_hash = password_hash.split("$", 2)
            salt = base64.b64decode(encoded_salt.encode("utf-8"))
            expected_hash = base64.b64decode(encoded_hash.encode("utf-8"))
        except (ValueError, UnicodeEncodeError):
            return False

        actual_hash = hashlib.scrypt(password_bytes, salt=salt, n=16384, r=8, p=1)
        return hmac.compare_digest(actual_hash, expected_hash)

    return False


def _get_jwt_secret() -> str:
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
    return secret


def _build_token_payload(
    *,
    user: AuthenticatedUser,
    expires_delta: timedelta,
    token_type: str,
) -> dict[str, Any]:
    expires_at = datetime.now(tz=UTC) + expires_delta
    return {
        "user_email": user.email,
        "workspace_id": str(user.workspace_id),
        "role": user.role.value,
        "token_version": user.token_version,
        "type": token_type,
        "exp": expires_at,
    }


def create_token_pair(user: AuthenticatedUser) -> TokenPair:
    settings = get_settings()
    secret = _get_jwt_secret()
    access_token_expire_minutes = getattr(settings, "access_token_expire_minutes", 15)
    refresh_token_expire_days = getattr(settings, "refresh_token_expire_days", 7)
    access_payload = _build_token_payload(
        user=user,
        expires_delta=timedelta(minutes=access_token_expire_minutes),
        token_type="access",
    )
    refresh_payload = _build_token_payload(
        user=user,
        expires_delta=timedelta(days=refresh_token_expire_days),
        token_type="refresh",
    )
    return TokenPair(
        access_token=jwt.encode(
            access_payload, secret, algorithm=settings.jwt_algorithm
        ),
        refresh_token=jwt.encode(
            refresh_payload, secret, algorithm=settings.jwt_algorithm
        ),
    )


def decode_access_token(token: str) -> TokenPayload:
    settings = get_settings()
    secret = _get_jwt_secret()

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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
        )

    token_payload = decode_access_token(credentials.credentials)
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

    return AuthenticatedUser.model_validate(user)


async def get_current_admin_for_workspace(
    workspace_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if current_user.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this workspace.",
        )

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        )

    return current_user

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    AuthenticatedUser,
    create_token_pair,
    decode_refresh_token,
    get_current_user,
    verify_password,
)
from app.infrastructure.database import get_db_session
from app.infrastructure.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginData,
    LoginRequest,
    LogoutData,
    RefreshData,
    RefreshRequest,
)
from app.schemas.common import ApiResponse, ResponseBuilder

router = APIRouter(prefix="/auth", tags=["auth"])


def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    return UserRepository(session)


@router.post(
    "/login/",
    response_model=ApiResponse[LoginData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiResponse[None]},
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
    },
)
async def login(
    payload: LoginRequest,
    user_repository: UserRepository = Depends(get_user_repository),
) -> ApiResponse[LoginData]:
    user = await user_repository.get_by_workspace_id_and_email(
        workspace_id=payload.workspace_id,
        email=payload.email,
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token_pair = create_token_pair(AuthenticatedUser.model_validate(user))
    return ResponseBuilder.success(
        LoginData.model_validate(token_pair.model_dump()),
        message="Login successful.",
    )


@router.post(
    "/refresh/",
    response_model=ApiResponse[RefreshData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiResponse[None]},
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
    },
)
async def refresh(
    payload: RefreshRequest,
    user_repository: UserRepository = Depends(get_user_repository),
) -> ApiResponse[RefreshData]:
    token_payload = decode_refresh_token(payload.refresh_token)
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
            detail="Refresh token is no longer valid.",
        )

    user = await user_repository.increment_token_version(user)
    token_pair = create_token_pair(AuthenticatedUser.model_validate(user))
    return ResponseBuilder.success(
        RefreshData.model_validate(token_pair.model_dump()),
        message="Token refreshed successfully.",
    )


@router.post(
    "/logout/",
    response_model=ApiResponse[LogoutData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
    },
)
async def logout(
    current_user: AuthenticatedUser = Depends(get_current_user),
    user_repository: UserRepository = Depends(get_user_repository),
) -> ApiResponse[LogoutData]:
    user = await user_repository.get_by_workspace_id_and_email(
        workspace_id=current_user.workspace_id,
        email=current_user.email,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user was not found.",
        )

    user = await user_repository.increment_token_version(user)
    return ResponseBuilder.success(
        LogoutData(token_version=user.token_version),
        message="Logout successful.",
    )

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_admin_for_workspace
from app.infrastructure.database import get_db_session
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.repositories.workspace_repository import WorkspaceRepository
from app.schemas.common import ApiResponse, ResponseBuilder
from app.schemas.user import (
    WorkspaceUserCreateData,
    WorkspaceUserCreateRequest,
    WorkspaceUserListData,
    WorkspaceUserUpdateData,
    WorkspaceUserUpdateRoleRequest,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/workspaces/{workspace_id}/users", tags=["workspace users"])


def get_user_service(
    session: AsyncSession = Depends(get_db_session),
) -> UserService:
    return UserService(
        UserRepository(session),
        WorkspaceRepository(session),
    )


@router.post(
    "/",
    response_model=ApiResponse[WorkspaceUserCreateData],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiResponse[None]},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiResponse[None]},
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
        status.HTTP_409_CONFLICT: {"model": ApiResponse[None]},
    },
)
async def create_workspace_user(
    workspace_id: uuid.UUID,
    payload: WorkspaceUserCreateRequest,
    service: UserService = Depends(get_user_service),
    _: AuthenticatedUser = Depends(get_current_admin_for_workspace),
) -> ApiResponse[WorkspaceUserCreateData]:
    data = await service.create_workspace_user(
        workspace_id=workspace_id,
        payload=payload,
    )
    return ResponseBuilder.created(data, message="User created successfully.")


@router.get(
    "/",
    response_model=ApiResponse[WorkspaceUserListData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
    },
)
async def list_workspace_users(
    workspace_id: uuid.UUID,
    service: UserService = Depends(get_user_service),
    _: AuthenticatedUser = Depends(get_current_admin_for_workspace),
) -> ApiResponse[WorkspaceUserListData]:
    data = await service.list_workspace_users(workspace_id)
    return ResponseBuilder.success(data, message="Users retrieved successfully.")


@router.patch(
    "/{user_id}/",
    response_model=ApiResponse[WorkspaceUserUpdateData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiResponse[None]},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiResponse[None]},
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
    },
)
async def update_workspace_user_role(
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: WorkspaceUserUpdateRoleRequest,
    service: UserService = Depends(get_user_service),
    _: AuthenticatedUser = Depends(get_current_admin_for_workspace),
) -> ApiResponse[WorkspaceUserUpdateData]:
    data = await service.update_workspace_user_role(
        workspace_id=workspace_id,
        user_id=user_id,
        payload=payload,
    )
    return ResponseBuilder.success(data, message="User role updated successfully.")

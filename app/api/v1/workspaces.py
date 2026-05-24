from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_admin_for_workspace
from app.infrastructure.database import get_db_session
from app.infrastructure.repositories.workspace_repository import WorkspaceRepository
from app.schemas.common import ApiResponse, ResponseBuilder
from app.schemas.workspace import (
    WorkspaceCreateData,
    WorkspaceCreateRequest,
    WorkspaceDetailsData,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def get_workspace_service(
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceService:
    return WorkspaceService(WorkspaceRepository(session))


@router.post(
    "/",
    response_model=ApiResponse[WorkspaceCreateData],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiResponse[None]},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiResponse[None]},
        status.HTTP_409_CONFLICT: {"model": ApiResponse[None]},
    },
)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    service: WorkspaceService = Depends(get_workspace_service),
) -> ApiResponse[WorkspaceCreateData]:
    data = await service.create_workspace(payload)
    return ResponseBuilder.created(data, message="Workspace created successfully.")


@router.get(
    "/{workspace_id}/",
    response_model=ApiResponse[WorkspaceDetailsData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
    },
)
async def get_workspace_details(
    workspace_id: uuid.UUID,
    service: WorkspaceService = Depends(get_workspace_service),
    _: AuthenticatedUser = Depends(get_current_admin_for_workspace),
) -> ApiResponse[WorkspaceDetailsData]:
    data = await service.get_workspace_details(workspace_id)
    return ResponseBuilder.success(data, message="Workspace retrieved successfully.")

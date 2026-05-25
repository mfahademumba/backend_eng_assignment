from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    AuthenticatedUser,
    get_current_admin_for_workspace,
    get_current_user_for_workspace,
)
from app.infrastructure.database import get_db_session
from app.infrastructure.repositories.policy_repository import PolicyRepository
from app.infrastructure.repositories.resource_repository import ResourceRepository
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.repositories.workspace_repository import WorkspaceRepository
from app.schemas.common import ApiResponse, ResponseBuilder
from app.schemas.resource import (
    ResourceCreateData,
    ResourceCreateRequest,
    ResourceDetailsData,
    ResourceListData,
    ResourceUpdateData,
    ResourceUpdateRequest,
)
from app.services.resource_service import ResourceService

router = APIRouter(prefix="/workspaces/{workspace_id}/resources", tags=["resources"])


def get_resource_service(
    session: AsyncSession = Depends(get_db_session),
) -> ResourceService:
    return ResourceService(
        ResourceRepository(session),
        PolicyRepository(session),
        UserRepository(session),
        WorkspaceRepository(session),
    )


@router.post(
    "/",
    response_model=ApiResponse[ResourceCreateData],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiResponse[None]},
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
        status.HTTP_409_CONFLICT: {"model": ApiResponse[None]},
    },
)
async def create_resource(
    workspace_id: uuid.UUID,
    payload: ResourceCreateRequest,
    service: ResourceService = Depends(get_resource_service),
    _: AuthenticatedUser = Depends(get_current_admin_for_workspace),
) -> ApiResponse[ResourceCreateData]:
    data = await service.create_resource(workspace_id=workspace_id, payload=payload)
    return ResponseBuilder.created(data, message="Resource created successfully.")


@router.get(
    "/",
    response_model=ApiResponse[ResourceListData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
    },
)
async def list_resources(
    workspace_id: uuid.UUID,
    service: ResourceService = Depends(get_resource_service),
    current_user: AuthenticatedUser = Depends(get_current_user_for_workspace),
) -> ApiResponse[ResourceListData]:
    data = await service.list_resources(
        workspace_id=workspace_id,
        current_user=current_user,
    )
    return ResponseBuilder.success(data, message="Resources retrieved successfully.")


@router.get(
    "/{resource_id}/",
    response_model=ApiResponse[ResourceDetailsData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
    },
)
async def get_resource_details(
    workspace_id: uuid.UUID,
    resource_id: uuid.UUID,
    service: ResourceService = Depends(get_resource_service),
    current_user: AuthenticatedUser = Depends(get_current_user_for_workspace),
) -> ApiResponse[ResourceDetailsData]:
    data = await service.get_resource_details(
        workspace_id=workspace_id,
        resource_id=resource_id,
        current_user=current_user,
    )
    return ResponseBuilder.success(data, message="Resource retrieved successfully.")


@router.patch(
    "/{resource_id}/",
    response_model=ApiResponse[ResourceUpdateData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiResponse[None]},
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
        status.HTTP_409_CONFLICT: {"model": ApiResponse[None]},
    },
)
async def update_resource(
    workspace_id: uuid.UUID,
    resource_id: uuid.UUID,
    payload: ResourceUpdateRequest,
    service: ResourceService = Depends(get_resource_service),
    _: AuthenticatedUser = Depends(get_current_admin_for_workspace),
) -> ApiResponse[ResourceUpdateData]:
    data = await service.update_resource(
        workspace_id=workspace_id,
        resource_id=resource_id,
        payload=payload,
    )
    return ResponseBuilder.success(data, message="Resource updated successfully.")


@router.delete(
    "/{resource_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
    },
)
async def delete_resource(
    workspace_id: uuid.UUID,
    resource_id: uuid.UUID,
    service: ResourceService = Depends(get_resource_service),
    _: AuthenticatedUser = Depends(get_current_admin_for_workspace),
) -> Response:
    await service.delete_resource(
        workspace_id=workspace_id,
        resource_id=resource_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

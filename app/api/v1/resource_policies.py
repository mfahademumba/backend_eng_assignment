from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_admin_for_workspace
from app.infrastructure.database import get_db_session
from app.infrastructure.repositories.policy_repository import PolicyRepository
from app.infrastructure.repositories.resource_repository import ResourceRepository
from app.infrastructure.repositories.workspace_repository import WorkspaceRepository
from app.schemas.common import ApiResponse, ResponseBuilder
from app.schemas.policy import (
    PolicyCreateData,
    PolicyCreateRequest,
    PolicyListData,
)
from app.services.policy_service import PolicyService

router = APIRouter(
    prefix="/workspaces/{workspace_id}/resources/{resource_id}/policies",
    tags=["resource policies"],
)


def get_policy_service(
    session: AsyncSession = Depends(get_db_session),
) -> PolicyService:
    return PolicyService(
        PolicyRepository(session),
        ResourceRepository(session),
        WorkspaceRepository(session),
    )


@router.post(
    "/",
    response_model=ApiResponse[PolicyCreateData],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiResponse[None]},
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
        status.HTTP_409_CONFLICT: {"model": ApiResponse[None]},
    },
)
async def create_resource_policy(
    workspace_id: uuid.UUID,
    resource_id: uuid.UUID,
    payload: PolicyCreateRequest,
    service: PolicyService = Depends(get_policy_service),
    _: AuthenticatedUser = Depends(get_current_admin_for_workspace),
) -> ApiResponse[PolicyCreateData]:
    data = await service.create_resource_policy(
        workspace_id=workspace_id,
        resource_id=resource_id,
        payload=payload,
    )
    return ResponseBuilder.created(data, message="Policy created successfully.")


@router.get(
    "/",
    response_model=ApiResponse[PolicyListData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
    },
)
async def list_resource_policies(
    workspace_id: uuid.UUID,
    resource_id: uuid.UUID,
    service: PolicyService = Depends(get_policy_service),
    _: AuthenticatedUser = Depends(get_current_admin_for_workspace),
) -> ApiResponse[PolicyListData]:
    data = await service.list_resource_policies(
        workspace_id=workspace_id,
        resource_id=resource_id,
    )
    return ResponseBuilder.success(data, message="Policies retrieved successfully.")


@router.delete(
    "/{policy_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
    },
)
async def delete_resource_policy(
    workspace_id: uuid.UUID,
    resource_id: uuid.UUID,
    policy_id: uuid.UUID,
    service: PolicyService = Depends(get_policy_service),
    _: AuthenticatedUser = Depends(get_current_admin_for_workspace),
) -> Response:
    await service.delete_resource_policy(
        workspace_id=workspace_id,
        resource_id=resource_id,
        policy_id=policy_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

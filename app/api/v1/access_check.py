from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, authorize_access_check
from app.infrastructure.database import get_db_session
from app.infrastructure.repositories.policy_repository import PolicyRepository
from app.infrastructure.repositories.resource_repository import ResourceRepository
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.repositories.workspace_repository import WorkspaceRepository
from app.schemas.access_check import AccessCheckData, AccessCheckRequest
from app.schemas.common import ApiResponse, ResponseBuilder
from app.services.access_check_service import AccessCheckService

router = APIRouter(prefix="/access-check", tags=["access check"])


def get_access_check_service(
    session: AsyncSession = Depends(get_db_session),
) -> AccessCheckService:
    return AccessCheckService(
        PolicyRepository(session),
        ResourceRepository(session),
        UserRepository(session),
        WorkspaceRepository(session),
    )


@router.post(
    "/",
    response_model=ApiResponse[AccessCheckData],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiResponse[None]},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiResponse[None]},
        status.HTTP_401_UNAUTHORIZED: {"model": ApiResponse[None]},
        status.HTTP_403_FORBIDDEN: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
    },
)
async def check_access(
    payload: AccessCheckRequest,
    service: AccessCheckService = Depends(get_access_check_service),
    _: AuthenticatedUser = Depends(authorize_access_check),
) -> ApiResponse[AccessCheckData]:
    data = await service.check_access(payload)
    return ResponseBuilder.success(data, message="Access check completed successfully.")

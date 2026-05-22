from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import AuthenticatedUser, get_current_admin_for_workspace, hash_password
from app.db import get_db_session
from app.models import User, UserRole, Workspace
from app.schemas.common import ApiResponse, ResponseBuilder
from app.schemas.workspace import (
    WorkspaceAdminCredentials,
    WorkspaceCreateData,
    WorkspaceCreateRequest,
    WorkspaceDetailsData,
    WorkspaceSummary,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _build_workspace_conflict_error(exc: IntegrityError) -> HTTPException:
    error_text = str(exc).lower()

    if "workspaces_name_key" in error_text:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A workspace with this name already exists.",
        )

    if "uq_users_workspace_email" in error_text:
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The admin email is already in use for this workspace.",
        )

    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Workspace creation failed because of a data conflict.",
    )


@router.post(
    "/",
    response_model=ApiResponse[WorkspaceCreateData],
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ApiResponse[WorkspaceCreateData]:
    workspace = Workspace(name=payload.name)
    admin_user = User(
        workspace=workspace,
        email=payload.admin_email,
        password_hash=hash_password(payload.admin_password),
        role=UserRole.ADMIN,
    )

    session.add_all([workspace, admin_user])

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise _build_workspace_conflict_error(exc) from exc

    await session.refresh(workspace)
    await session.refresh(admin_user)

    data = WorkspaceCreateData(
        workspace=WorkspaceSummary.model_validate(workspace),
        admin_credentials=WorkspaceAdminCredentials(
            user_id=admin_user.id,
            email=admin_user.email,
            role=admin_user.role,
        ),
    )
    return ResponseBuilder.created(data, message="Workspace created successfully.")


@router.get(
    "/{workspace_id}/",
    response_model=ApiResponse[WorkspaceDetailsData],
    status_code=status.HTTP_200_OK,
)
async def get_workspace_details(
    workspace_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
    _: AuthenticatedUser = Depends(get_current_admin_for_workspace),
) -> ApiResponse[WorkspaceDetailsData]:
    workspace = await session.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    data = WorkspaceDetailsData(workspace=WorkspaceSummary.model_validate(workspace))
    return ResponseBuilder.success(data, message="Workspace retrieved successfully.")

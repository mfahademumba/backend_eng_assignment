from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth import hash_password
from app.infrastructure.repositories.workspace_repository import WorkspaceRepository
from app.models import User, UserRole, Workspace
from app.schemas.workspace import (
    WorkspaceAdminCredentials,
    WorkspaceCreateData,
    WorkspaceCreateRequest,
    WorkspaceDetailsData,
    WorkspaceSummary,
)


class WorkspaceService:
    def __init__(self, workspace_repository: WorkspaceRepository) -> None:
        self.workspace_repository = workspace_repository

    async def create_workspace(
        self,
        payload: WorkspaceCreateRequest,
    ) -> WorkspaceCreateData:
        workspace = Workspace(name=payload.name)
        admin_user = User(
            workspace=workspace,
            email=payload.admin_email,
            password_hash=hash_password(payload.admin_password),
            role=UserRole.ADMIN,
        )

        try:
            workspace, admin_user = await self.workspace_repository.create_with_admin(
                workspace=workspace,
                admin_user=admin_user,
            )
        except IntegrityError as exc:
            await self.workspace_repository.rollback()
            raise self._build_workspace_conflict_error(exc) from exc

        return WorkspaceCreateData(
            workspace=WorkspaceSummary.model_validate(workspace),
            admin_credentials=WorkspaceAdminCredentials(
                user_id=admin_user.id,
                email=admin_user.email,
                role=admin_user.role,
            ),
        )

    async def get_workspace_details(
        self, workspace_id: uuid.UUID
    ) -> WorkspaceDetailsData:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found.",
            )

        return WorkspaceDetailsData(
            workspace=WorkspaceSummary.model_validate(workspace),
        )

    @staticmethod
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

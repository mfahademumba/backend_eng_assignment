from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth import hash_password
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.repositories.workspace_repository import WorkspaceRepository
from app.models import User
from app.schemas.user import (
    WorkspaceUserCreateData,
    WorkspaceUserCreateRequest,
    WorkspaceUserListData,
    WorkspaceUserSummary,
    WorkspaceUserUpdateData,
    WorkspaceUserUpdateRoleRequest,
)


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self.user_repository = user_repository
        self.workspace_repository = workspace_repository

    async def create_workspace_user(
        self,
        *,
        workspace_id: uuid.UUID,
        payload: WorkspaceUserCreateRequest,
    ) -> WorkspaceUserCreateData:
        await self._ensure_workspace_exists(workspace_id)

        user = User(
            workspace_id=workspace_id,
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=payload.role,
        )

        try:
            user = await self.user_repository.create(user)
        except IntegrityError as exc:
            await self.user_repository.rollback()
            raise self._build_user_conflict_error(exc) from exc

        return WorkspaceUserCreateData(user=WorkspaceUserSummary.model_validate(user))

    async def list_workspace_users(
        self,
        workspace_id: uuid.UUID,
    ) -> WorkspaceUserListData:
        await self._ensure_workspace_exists(workspace_id)
        users = await self.user_repository.list_by_workspace_id(workspace_id)
        return WorkspaceUserListData(
            users=[WorkspaceUserSummary.model_validate(user) for user in users]
        )

    async def update_workspace_user_role(
        self,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: WorkspaceUserUpdateRoleRequest,
    ) -> WorkspaceUserUpdateData:
        await self._ensure_workspace_exists(workspace_id)

        user = await self.user_repository.get_by_workspace_id_and_user_id(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        user.role = payload.role
        user = await self.user_repository.update_role(user)
        return WorkspaceUserUpdateData(user=WorkspaceUserSummary.model_validate(user))

    async def _ensure_workspace_exists(self, workspace_id: uuid.UUID) -> None:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found.",
            )

    @staticmethod
    def _build_user_conflict_error(exc: IntegrityError) -> HTTPException:
        error_text = str(exc).lower()

        if "uq_users_workspace_email" in error_text:
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists in this workspace.",
            )

        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User creation failed because of a data conflict.",
        )

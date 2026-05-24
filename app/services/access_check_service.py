from __future__ import annotations

from fastapi import HTTPException, status

from app.infrastructure.repositories.policy_repository import PolicyRepository
from app.infrastructure.repositories.resource_repository import ResourceRepository
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.repositories.workspace_repository import WorkspaceRepository
from app.models import UserRole
from app.policy_engine import admin_bypass_result, policy_eval
from app.schemas.access_check import AccessCheckData, AccessCheckRequest


class AccessCheckService:
    def __init__(
        self,
        policy_repository: PolicyRepository,
        resource_repository: ResourceRepository,
        user_repository: UserRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self.policy_repository = policy_repository
        self.resource_repository = resource_repository
        self.user_repository = user_repository
        self.workspace_repository = workspace_repository

    async def check_access(self, payload: AccessCheckRequest) -> AccessCheckData:
        workspace = await self.workspace_repository.get_by_id(payload.workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found.",
            )

        user = await self.user_repository.get_by_workspace_id_and_user_id(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        resource = await self.resource_repository.get_by_workspace_id_and_resource_id(
            workspace_id=payload.workspace_id,
            resource_id=payload.resource_id,
        )
        if resource is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found.",
            )

        if user.role == UserRole.ADMIN:
            result = admin_bypass_result(user)
        else:
            effective_policies = (
                await self.policy_repository.list_effective_for_resource(
                    workspace_id=payload.workspace_id,
                    resource_id=payload.resource_id,
                )
            )
            result = policy_eval(effective_policies, user)

        return AccessCheckData(
            access_granted=result.access_granted,
            reason=result.reason,
            matched_policy_id=result.matched_policy_id,
        )

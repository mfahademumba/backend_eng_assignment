from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.infrastructure.repositories.policy_repository import PolicyRepository
from app.infrastructure.repositories.resource_repository import ResourceRepository
from app.infrastructure.repositories.workspace_repository import WorkspaceRepository
from app.models import Policy
from app.schemas.policy import (
    PolicyCreateData,
    PolicyCreateRequest,
    PolicyDeleteData,
    PolicyListData,
    PolicySummary,
)


class PolicyService:
    def __init__(
        self,
        policy_repository: PolicyRepository,
        resource_repository: ResourceRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self.policy_repository = policy_repository
        self.resource_repository = resource_repository
        self.workspace_repository = workspace_repository

    async def create_resource_policy(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
        payload: PolicyCreateRequest,
    ) -> PolicyCreateData:
        await self._ensure_workspace_and_resource_exist(workspace_id, resource_id)

        policy = Policy(
            workspace_id=workspace_id,
            name=payload.name,
            effect=payload.effect,
            target_type=payload.target_type,
            target_value=payload.target_value,
            priority=payload.priority,
        )
        try:
            policy = await self.policy_repository.create_for_resource(
                policy=policy,
                resource_id=resource_id,
            )
        except IntegrityError as exc:
            await self.policy_repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Policy creation failed because of a data conflict.",
            ) from exc

        return PolicyCreateData(policy=PolicySummary.model_validate(policy))

    async def list_resource_policies(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
    ) -> PolicyListData:
        await self._ensure_workspace_and_resource_exist(workspace_id, resource_id)
        policies = await self.policy_repository.list_for_resource(
            workspace_id=workspace_id,
            resource_id=resource_id,
        )
        return PolicyListData(
            policies=[PolicySummary.model_validate(policy) for policy in policies]
        )

    async def delete_resource_policy(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> PolicyDeleteData:
        await self._ensure_workspace_and_resource_exist(workspace_id, resource_id)
        policy = await self.policy_repository.get_for_resource(
            workspace_id=workspace_id,
            resource_id=resource_id,
            policy_id=policy_id,
        )
        if policy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found.",
            )

        await self.policy_repository.delete_for_resource(
            workspace_id=workspace_id,
            resource_id=resource_id,
            policy_id=policy_id,
        )
        return PolicyDeleteData(policy_id=policy_id)

    async def _ensure_workspace_and_resource_exist(
        self,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
    ) -> None:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found.",
            )

        resource = await self.resource_repository.get_by_workspace_id_and_resource_id(
            workspace_id=workspace_id,
            resource_id=resource_id,
        )
        if resource is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found.",
            )

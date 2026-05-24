from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth import AuthenticatedUser
from app.infrastructure.repositories.policy_repository import PolicyRepository
from app.infrastructure.repositories.resource_repository import ResourceRepository
from app.infrastructure.repositories.user_repository import UserRepository
from app.infrastructure.repositories.workspace_repository import WorkspaceRepository
from app.models import Resource, UserRole
from app.policy_engine import admin_bypass_result, policy_eval
from app.schemas.policy import PolicySummary
from app.schemas.resource import (
    ResourceCreateData,
    ResourceCreateRequest,
    ResourceDeleteData,
    ResourceDetailsData,
    ResourceListData,
    ResourceSummary,
    ResourceUpdateData,
    ResourceUpdateRequest,
)


class ResourceService:
    def __init__(
        self,
        resource_repository: ResourceRepository,
        policy_repository: PolicyRepository,
        user_repository: UserRepository,
        workspace_repository: WorkspaceRepository,
    ) -> None:
        self.resource_repository = resource_repository
        self.policy_repository = policy_repository
        self.user_repository = user_repository
        self.workspace_repository = workspace_repository

    async def create_resource(
        self,
        *,
        workspace_id: uuid.UUID,
        payload: ResourceCreateRequest,
    ) -> ResourceCreateData:
        await self._ensure_workspace_exists(workspace_id)
        resource = Resource(
            workspace_id=workspace_id,
            name=payload.name,
            type=payload.type,
            description=payload.description,
            status=payload.status,
        )

        try:
            resource = await self.resource_repository.create(resource)
        except IntegrityError as exc:
            await self.resource_repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resource creation failed because of a data conflict.",
            ) from exc

        return ResourceCreateData(resource=ResourceSummary.model_validate(resource))

    async def list_resources(
        self,
        *,
        workspace_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> ResourceListData:
        await self._ensure_workspace_exists(workspace_id)
        user = await self._get_current_workspace_user(current_user)
        resources = await self.resource_repository.list_by_workspace_id(workspace_id)

        if user.role != UserRole.ADMIN:
            accessible_resources = []
            for resource in resources:
                if await self._user_can_access_resource(
                    user=user, resource_id=resource.id
                ):
                    accessible_resources.append(resource)
            resources = accessible_resources

        return ResourceListData(
            resources=[
                ResourceSummary.model_validate(resource) for resource in resources
            ]
        )

    async def get_resource_details(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> ResourceDetailsData:
        await self._ensure_workspace_exists(workspace_id)
        user = await self._get_current_workspace_user(current_user)
        resource = await self._get_resource_or_404(workspace_id, resource_id)

        if user.role != UserRole.ADMIN and not await self._user_can_access_resource(
            user=user,
            resource_id=resource_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this resource.",
            )

        policies = await self.policy_repository.list_for_resource(
            workspace_id=workspace_id,
            resource_id=resource_id,
        )
        return ResourceDetailsData(
            resource=ResourceSummary.model_validate(resource),
            policies=[PolicySummary.model_validate(policy) for policy in policies],
        )

    async def update_resource(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
        payload: ResourceUpdateRequest,
    ) -> ResourceUpdateData:
        await self._ensure_workspace_exists(workspace_id)
        resource = await self._get_resource_or_404(workspace_id, resource_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(resource, field, value)

        try:
            resource = await self.resource_repository.update(resource)
        except IntegrityError as exc:
            await self.resource_repository.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Resource update failed because of a data conflict.",
            ) from exc

        return ResourceUpdateData(resource=ResourceSummary.model_validate(resource))

    async def delete_resource(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
    ) -> ResourceDeleteData:
        await self._ensure_workspace_exists(workspace_id)
        await self._get_resource_or_404(workspace_id, resource_id)
        await self.resource_repository.delete_by_workspace_id_and_resource_id(
            workspace_id=workspace_id,
            resource_id=resource_id,
        )
        return ResourceDeleteData(resource_id=resource_id)

    async def _ensure_workspace_exists(self, workspace_id: uuid.UUID) -> None:
        workspace = await self.workspace_repository.get_by_id(workspace_id)
        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found.",
            )

    async def _get_resource_or_404(
        self,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
    ) -> Resource:
        resource = await self.resource_repository.get_by_workspace_id_and_resource_id(
            workspace_id=workspace_id,
            resource_id=resource_id,
        )
        if resource is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found.",
            )
        return resource

    async def _get_current_workspace_user(self, current_user: AuthenticatedUser):
        user = await self.user_repository.get_by_workspace_id_and_user_id(
            workspace_id=current_user.workspace_id,
            user_id=current_user.id,
        )
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authenticated user was not found.",
            )
        return user

    async def _user_can_access_resource(self, *, user, resource_id: uuid.UUID) -> bool:
        if user.role == UserRole.ADMIN:
            return admin_bypass_result(user).access_granted

        effective_policies = await self.policy_repository.list_effective_for_resource(
            workspace_id=user.workspace_id,
            resource_id=resource_id,
        )
        return policy_eval(effective_policies, user).access_granted

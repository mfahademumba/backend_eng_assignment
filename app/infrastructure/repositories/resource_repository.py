from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Resource


class ResourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, resource: Resource) -> Resource:
        self.session.add_all([resource])
        await self.session.commit()
        await self.session.refresh(resource)
        return resource

    async def list_by_workspace_id(self, workspace_id: uuid.UUID) -> list[Resource]:
        result = await self.session.scalars(
            select(Resource)
            .where(Resource.workspace_id == workspace_id)
            .order_by(Resource.created_at.asc(), Resource.name.asc(), Resource.id.asc())
        )
        return list(result.all())

    async def get_by_workspace_id_and_resource_id(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
    ) -> Resource | None:
        return await self.session.scalar(
            select(Resource).where(
                Resource.id == resource_id,
                Resource.workspace_id == workspace_id,
            )
        )

    async def update(self, resource: Resource) -> Resource:
        await self.session.commit()
        await self.session.refresh(resource)
        return resource

    async def delete_by_workspace_id_and_resource_id(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
    ) -> None:
        await self.session.execute(
            delete(Resource).where(
                Resource.id == resource_id,
                Resource.workspace_id == workspace_id,
            )
        )
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

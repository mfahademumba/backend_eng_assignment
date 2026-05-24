from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Resource


class ResourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_workspace_id_and_resource_id(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
    ) -> Resource | None:
        resource = await self.session.get(Resource, resource_id)
        if resource is None or resource.workspace_id != workspace_id:
            return None
        return resource

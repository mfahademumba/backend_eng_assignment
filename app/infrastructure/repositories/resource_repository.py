from __future__ import annotations

import uuid

from sqlalchemy import select
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
        return await self.session.scalar(
            select(Resource).where(
                Resource.id == resource_id,
                Resource.workspace_id == workspace_id,
            )
        )

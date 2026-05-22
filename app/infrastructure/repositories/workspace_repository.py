from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Workspace


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_with_admin(
        self,
        *,
        workspace: Workspace,
        admin_user: User,
    ) -> tuple[Workspace, User]:
        self.session.add_all([workspace, admin_user])
        await self.session.commit()
        await self.session.refresh(workspace)
        await self.session.refresh(admin_user)
        return workspace, admin_user

    async def rollback(self) -> None:
        await self.session.rollback()

    async def get_by_id(self, workspace_id: uuid.UUID) -> Workspace | None:
        return await self.session.get(Workspace, workspace_id)

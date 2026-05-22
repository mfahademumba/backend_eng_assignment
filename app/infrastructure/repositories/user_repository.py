from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_workspace_id_and_email(
        self,
        *,
        workspace_id: uuid.UUID,
        email: str,
    ) -> User | None:
        return await self.session.scalar(
            select(User).where(
                User.workspace_id == workspace_id,
                User.email == email,
            )
        )

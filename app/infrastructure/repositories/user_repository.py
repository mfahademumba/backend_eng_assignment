from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user: User) -> User:
        self.session.add_all([user])
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def rollback(self) -> None:
        await self.session.rollback()

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

    async def list_by_workspace_id(self, workspace_id: uuid.UUID) -> list[User]:
        result = await self.session.scalars(
            select(User)
            .where(User.workspace_id == workspace_id)
            .order_by(User.created_at.asc(), User.email.asc())
        )
        return list(result.all())

    async def get_by_workspace_id_and_user_id(
        self,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> User | None:
        user = await self.session.get(User, user_id)
        if user is None or user.workspace_id != workspace_id:
            return None
        return user

    async def update_role(self, user: User) -> User:
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def increment_token_version(self, user: User) -> User:
        user.token_version += 1
        await self.session.commit()
        await self.session.refresh(user)
        return user

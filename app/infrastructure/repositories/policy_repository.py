from __future__ import annotations

import uuid

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import EffectivePolicy, Policy


class PolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_for_resource(
        self,
        *,
        policy: Policy,
        resource_id: uuid.UUID,
    ) -> Policy:
        self.session.add_all([policy])
        await self.session.flush()
        effective_policy = EffectivePolicy(
            workspace_id=policy.workspace_id,
            resource_id=resource_id,
            policy_id=policy.id,
        )
        self.session.add_all([effective_policy])
        await self.session.commit()
        await self.session.refresh(policy)
        return policy

    async def list_for_resource(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
    ) -> list[Policy]:
        result = await self.session.scalars(
            select(Policy)
            .join(EffectivePolicy, EffectivePolicy.policy_id == Policy.id)
            .where(
                Policy.workspace_id == workspace_id,
                EffectivePolicy.workspace_id == workspace_id,
                EffectivePolicy.resource_id == resource_id,
            )
            .order_by(Policy.priority.desc(), Policy.created_at.asc(), Policy.id.asc())
        )
        return list(result.all())

    async def list_effective_for_resource(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
    ) -> list[EffectivePolicy]:
        result = await self.session.scalars(
            select(EffectivePolicy)
            .options(selectinload(EffectivePolicy.policy))
            .join(Policy, EffectivePolicy.policy_id == Policy.id)
            .where(
                EffectivePolicy.workspace_id == workspace_id,
                EffectivePolicy.resource_id == resource_id,
            )
            .order_by(Policy.priority.desc(), Policy.created_at.asc(), Policy.id.asc())
        )
        return list(result.all())

    async def get_for_resource(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> Policy | None:
        return await self.session.scalar(
            select(Policy)
            .join(EffectivePolicy, EffectivePolicy.policy_id == Policy.id)
            .where(
                Policy.id == policy_id,
                Policy.workspace_id == workspace_id,
                EffectivePolicy.workspace_id == workspace_id,
                EffectivePolicy.resource_id == resource_id,
            )
        )

    async def delete_for_resource(
        self,
        *,
        workspace_id: uuid.UUID,
        resource_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> None:
        linked_to_resource = exists().where(
            EffectivePolicy.policy_id == Policy.id,
            EffectivePolicy.workspace_id == workspace_id,
            EffectivePolicy.resource_id == resource_id,
        )
        await self.session.execute(
            delete(Policy).where(
                Policy.id == policy_id,
                Policy.workspace_id == workspace_id,
                linked_to_resource,
            )
        )
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

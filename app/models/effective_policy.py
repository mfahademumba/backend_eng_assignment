from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKeyConstraint, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.policy import Policy
    from app.models.resource import Resource
    from app.models.workspace import Workspace


class EffectivePolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "effective_policies"
    __table_args__ = (
        UniqueConstraint(
            "resource_id", "policies_id", name="uq_effective_policies_resource_policy"
        ),
        ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["resource_id", "workspace_id"],
            ["resources.id", "resources.workspace_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["policies_id", "workspace_id"],
            ["policies.id", "policies.workspace_id"],
            ondelete="CASCADE",
        ),
        Index(
            "ix_effective_policies_workspace_resource", "workspace_id", "resource_id"
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        "policies_id", UUID(as_uuid=True), nullable=False
    )

    workspace: Mapped["Workspace"] = relationship(
        "Workspace",
        back_populates="effective_policies",
        overlaps="policy,resource,effective_policies",
    )
    resource: Mapped["Resource"] = relationship(
        "Resource",
        back_populates="effective_policies",
        overlaps="workspace,policy,effective_policies",
    )
    policy: Mapped["Policy"] = relationship(
        "Policy",
        back_populates="effective_policies",
        overlaps="workspace,resource,effective_policies",
    )


__all__ = ["EffectivePolicy"]

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, ResourceType, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.effective_policy import EffectivePolicy
    from app.models.workspace import Workspace


class Resource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resources"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id", name="uq_resources_id_workspace_id"),
        CheckConstraint(
            "type IN ('document', 'database', 'service', 'api', 'file')",
            name="ck_resources_type_valid",
        ),
        Index("ix_resources_workspace_id", "workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[ResourceType] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="resources"
    )
    effective_policies: Mapped[list["EffectivePolicy"]] = relationship(
        "EffectivePolicy",
        back_populates="resource",
        cascade="all, delete-orphan",
        overlaps="workspace,policy,effective_policies",
    )


__all__ = ["Resource"]

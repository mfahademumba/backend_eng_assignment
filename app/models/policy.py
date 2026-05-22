from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PolicyEffect, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.effective_policy import EffectivePolicy
    from app.models.workspace import Workspace


class Policy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "policies"
    __table_args__ = (
        CheckConstraint("priority > 0", name="ck_policies_priority_positive"),
        UniqueConstraint("id", "workspace_id", name="uq_policies_id_workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    effect: Mapped[PolicyEffect] = mapped_column(
        Enum(PolicyEffect, name="policy_effect_enum", native_enum=True),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_value: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)

    workspace: Mapped["Workspace"] = relationship(
        "Workspace", back_populates="policies"
    )
    effective_policies: Mapped[list["EffectivePolicy"]] = relationship(
        "EffectivePolicy",
        back_populates="policy",
        cascade="all, delete-orphan",
        overlaps="workspace,resource,effective_policies",
    )


__all__ = ["Policy"]

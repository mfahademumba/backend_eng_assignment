from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.effective_policy import EffectivePolicy
    from app.models.policy import Policy
    from app.models.resource import Resource
    from app.models.user import User


class Workspace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    policies: Mapped[list["Policy"]] = relationship(
        "Policy",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    resources: Mapped[list["Resource"]] = relationship(
        "Resource",
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    effective_policies: Mapped[list["EffectivePolicy"]] = relationship(
        "EffectivePolicy",
        back_populates="workspace",
        cascade="all, delete-orphan",
        overlaps="policy,resource",
    )


__all__ = ["Workspace"]

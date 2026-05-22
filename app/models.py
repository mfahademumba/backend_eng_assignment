from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


class PolicyEffect(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"


class Workspace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    users: Mapped[list[User]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    policies: Mapped[list[Policy]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    resources: Mapped[list[Resource]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    effective_policies: Mapped[list[EffectivePolicy]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
        overlaps="policy,resource",
    )


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("workspace_id", "email", name="uq_users_workspace_email"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role_enum", native_enum=True),
        nullable=False,
        server_default=text("'user'"),
    )
    token_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    workspace: Mapped[Workspace] = relationship(back_populates="users")


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

    workspace: Mapped[Workspace] = relationship(back_populates="policies")
    effective_policies: Mapped[list[EffectivePolicy]] = relationship(
        back_populates="policy",
        cascade="all, delete-orphan",
        overlaps="workspace,resource,effective_policies",
    )


class Resource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resources"
    __table_args__ = (
        UniqueConstraint("id", "workspace_id", name="uq_resources_id_workspace_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    workspace: Mapped[Workspace] = relationship(back_populates="resources")
    effective_policies: Mapped[list[EffectivePolicy]] = relationship(
        back_populates="resource",
        cascade="all, delete-orphan",
        overlaps="workspace,policy,effective_policies",
    )


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
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(
        "policies_id", UUID(as_uuid=True), nullable=False
    )

    workspace: Mapped[Workspace] = relationship(
        back_populates="effective_policies",
        overlaps="policy,resource,effective_policies",
    )
    resource: Mapped[Resource] = relationship(
        back_populates="effective_policies",
        overlaps="workspace,policy,effective_policies",
    )
    policy: Mapped[Policy] = relationship(
        back_populates="effective_policies",
        overlaps="workspace,resource,effective_policies",
    )


__all__ = [
    "Base",
    "Workspace",
    "User",
    "Policy",
    "Resource",
    "EffectivePolicy",
    "UserRole",
    "PolicyEffect",
]

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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


class ResourceType(str, enum.Enum):
    DOCUMENT = "document"
    DATABASE = "database"
    SERVICE = "service"
    API = "api"
    FILE = "file"


__all__ = [
    "Base",
    "UUIDPrimaryKeyMixin",
    "TimestampMixin",
    "UserRole",
    "PolicyEffect",
    "ResourceType",
]

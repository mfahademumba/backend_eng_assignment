"""initial schema

Revision ID: 20260524_0001
Revises:
Create Date: 2026-05-24 00:00:00.000000+00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260524_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


user_role_enum = postgresql.ENUM(
    "ADMIN", "USER", name="user_role_enum", create_type=False
)
policy_effect_enum = postgresql.ENUM(
    "ALLOW", "DENY", name="policy_effect_enum", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    user_role_enum.create(bind, checkfirst=True)
    policy_effect_enum.create(bind, checkfirst=True)

    op.create_table(
        "workspaces",
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "policies",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("effect", policy_effect_enum, nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_value", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("priority > 0", name="ck_policies_priority_positive"),
        sa.CheckConstraint(
            "target_type IN ('role', 'user')",
            name="ck_policies_target_type_valid",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "workspace_id", name="uq_policies_id_workspace_id"),
    )
    op.create_table(
        "resources",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type IN ('document', 'database', 'service', 'api', 'file')",
            name="ck_resources_type_valid",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "workspace_id", name="uq_resources_id_workspace_id"),
    )
    op.create_index("ix_resources_workspace_id", "resources", ["workspace_id"])
    op.create_table(
        "users",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role", user_role_enum, server_default=sa.text("'USER'"), nullable=False
        ),
        sa.Column(
            "token_version", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "email", name="uq_users_workspace_email"),
    )
    op.create_index("ix_users_workspace_id_id", "users", ["workspace_id", "id"])
    op.create_foreign_key(
        "fk_policies_resource_workspace",
        "policies",
        "resources",
        ["resource_id", "workspace_id"],
        ["id", "workspace_id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_policies_workspace_resource",
        "policies",
        ["workspace_id", "resource_id"],
    )
    op.create_index(
        "ix_policies_workspace_resource_priority",
        "policies",
        ["workspace_id", "resource_id", "priority"],
    )
    op.create_table(
        "effective_policies",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policies_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["resource_id", "workspace_id"],
            ["resources.id", "resources.workspace_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["policies_id", "workspace_id"],
            ["policies.id", "policies.workspace_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "resource_id", "policies_id", name="uq_effective_policies_resource_policy"
        ),
    )
    op.create_index(
        "ix_effective_policies_workspace_resource",
        "effective_policies",
        ["workspace_id", "resource_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table("effective_policies")
    op.drop_table("users")
    op.drop_table("policies")
    op.drop_table("resources")
    op.drop_table("workspaces")
    policy_effect_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)

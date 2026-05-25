from __future__ import annotations

from typing import cast

from sqlalchemy import Table

from app.models import EffectivePolicy, Policy, Resource, Workspace


def test_workspace_relationships_are_configured_to_cascade_deletes() -> None:
    relationships = Workspace.__mapper__.relationships

    assert "delete-orphan" in relationships["users"].cascade
    assert "delete-orphan" in relationships["resources"].cascade
    assert "delete-orphan" in relationships["policies"].cascade
    assert "delete-orphan" in relationships["effective_policies"].cascade


def test_resource_policy_foreign_keys_are_configured_for_database_cascade() -> None:
    resource_table = cast(Table, Resource.__table__)
    policy_table = cast(Table, Policy.__table__)
    effective_policy_table = cast(Table, EffectivePolicy.__table__)

    resource_workspace_fk = next(
        fk for fk in resource_table.foreign_keys if fk.parent.name == "workspace_id"
    )
    policy_workspace_fk = next(
        fk for fk in policy_table.foreign_keys if fk.parent.name == "workspace_id"
    )
    policy_resource_fk_constraints = [
        constraint
        for constraint in policy_table.foreign_key_constraints
        if {element.parent.name for element in constraint.elements}
        == {"resource_id", "workspace_id"}
    ]
    effective_policy_foreign_key_ondeletes = {
        fk.ondelete
        for constraint in effective_policy_table.foreign_key_constraints
        for fk in constraint.elements
    }

    assert resource_workspace_fk.ondelete == "CASCADE"
    assert policy_workspace_fk.ondelete == "CASCADE"
    assert policy_resource_fk_constraints == []
    assert effective_policy_foreign_key_ondeletes == {"CASCADE"}

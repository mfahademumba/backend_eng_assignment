from __future__ import annotations

from app.models import EffectivePolicy, Policy, Resource, Workspace


def test_workspace_relationships_are_configured_to_cascade_deletes() -> None:
    relationships = Workspace.__mapper__.relationships

    assert "delete-orphan" in relationships["users"].cascade
    assert "delete-orphan" in relationships["resources"].cascade
    assert "delete-orphan" in relationships["policies"].cascade
    assert "delete-orphan" in relationships["effective_policies"].cascade


def test_resource_policy_foreign_keys_are_configured_for_database_cascade() -> None:
    resource_workspace_fk = next(
        fk for fk in Resource.__table__.foreign_keys if fk.parent.name == "workspace_id"
    )
    policy_workspace_fk = next(
        fk for fk in Policy.__table__.foreign_keys if fk.parent.name == "workspace_id"
    )
    policy_resource_fk_ondelete = next(
        constraint.ondelete
        for constraint in Policy.__table__.foreign_key_constraints
        if {element.parent.name for element in constraint.elements}
        == {"resource_id", "workspace_id"}
    )
    effective_policy_foreign_key_ondeletes = {
        fk.ondelete
        for constraint in EffectivePolicy.__table__.foreign_key_constraints
        for fk in constraint.elements
    }

    assert resource_workspace_fk.ondelete == "CASCADE"
    assert policy_workspace_fk.ondelete == "CASCADE"
    assert policy_resource_fk_ondelete == "CASCADE"
    assert effective_policy_foreign_key_ondeletes == {"CASCADE"}

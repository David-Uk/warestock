"""Enforce audit log immutability and add read indexes

Adds the database-level append-only guarantee for ``audit_logs`` (the ORM guard
in ``app.models.audit_log`` only protects in-process edits) plus the composite
indexes the filtered audit-listing endpoint reads through.

The ``user_id`` / ``organisation_id`` / ``warehouse_id`` foreign keys are
declared ``ON DELETE SET NULL``, so the trigger permits those columns to be
cleared when the referenced record is deleted — otherwise the audit trail would
be destroyed alongside the user or organisation it describes. Re-pointing them
at a different subject, and any change to an evidence column, is rejected.

Revision ID: 011
Revises: 010
Create Date: 2026-09-30

"""

from collections.abc import Sequence

from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CREATE_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION audit_logs_immutable() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'audit_logs is append-only: DELETE is not permitted'
            USING ERRCODE = 'restrict_violation';
    END IF;

    IF NEW.id IS DISTINCT FROM OLD.id
        OR NEW.created_at IS DISTINCT FROM OLD.created_at
        OR NEW.updated_at IS DISTINCT FROM OLD.updated_at
        OR NEW.action IS DISTINCT FROM OLD.action
        OR NEW.resource_type IS DISTINCT FROM OLD.resource_type
        OR NEW.resource_id IS DISTINCT FROM OLD.resource_id
        OR NEW.payload::jsonb IS DISTINCT FROM OLD.payload::jsonb
        OR NEW.role IS DISTINCT FROM OLD.role
        OR NEW.ip_address IS DISTINCT FROM OLD.ip_address
        OR NEW.user_agent IS DISTINCT FROM OLD.user_agent
    THEN
        RAISE EXCEPTION 'audit_logs is append-only: UPDATE is not permitted'
            USING ERRCODE = 'restrict_violation';
    END IF;

    IF (NEW.user_id IS NOT NULL AND NEW.user_id IS DISTINCT FROM OLD.user_id)
        OR (NEW.organisation_id IS NOT NULL
            AND NEW.organisation_id IS DISTINCT FROM OLD.organisation_id)
        OR (NEW.warehouse_id IS NOT NULL
            AND NEW.warehouse_id IS DISTINCT FROM OLD.warehouse_id)
    THEN
        RAISE EXCEPTION 'audit_logs is append-only: reference columns may only be cleared'
            USING ERRCODE = 'restrict_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_TRIGGER = """
CREATE TRIGGER audit_logs_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable();
"""

DROP_TRIGGER_AND_FUNCTION = """
DROP TRIGGER IF EXISTS audit_logs_immutable ON audit_logs;
DROP FUNCTION IF EXISTS audit_logs_immutable();
"""


def upgrade() -> None:
    # Audit reads are always scoped by organisation or user and ordered by
    # recency, so index the pair rather than each column in isolation.
    # ``if_not_exists`` tolerates databases where ``create_all`` already
    # created the same indexes from ``AuditLog.__table_args__``.
    op.create_index(
        "ix_audit_logs_org_created_at",
        "audit_logs",
        ["organisation_id", "created_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_audit_logs_user_created_at",
        "audit_logs",
        ["user_id", "created_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_audit_logs_action_created_at",
        "audit_logs",
        ["action", "created_at"],
        if_not_exists=True,
    )

    op.execute(CREATE_TRIGGER_FUNCTION)
    op.execute("DROP TRIGGER IF EXISTS audit_logs_immutable ON audit_logs;")
    op.execute(CREATE_TRIGGER)


def downgrade() -> None:
    op.execute(DROP_TRIGGER_AND_FUNCTION)

    op.drop_index("ix_audit_logs_action_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_org_created_at", table_name="audit_logs")

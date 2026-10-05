import uuid

from sqlalchemy import JSON, Connection, ForeignKey, Index, String, Table, event, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# Database-level immutability. The ORM guard below stops accidental in-process
# edits, but anything using raw SQL or a different client would still be able to
# rewrite history, so the trigger is the real enforcement boundary. It is
# installed here (not only in the migration) so databases built with
# ``Base.metadata.create_all`` — the test suite and local dev bootstrapping —
# get exactly the same guarantees as a migrated database.
#
# The three foreign keys use ``ON DELETE SET NULL`` so the trail outlives the
# user, organisation or warehouse it refers to. The trigger therefore permits
# *nulling* those columns and nothing else: values can never be re-pointed at a
# different subject, and no evidence column can ever change.
AUDIT_LOG_IMMUTABILITY_STATEMENTS = (
    """
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
    """,
    """
    DROP TRIGGER IF EXISTS audit_logs_immutable ON audit_logs;
    CREATE TRIGGER audit_logs_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION audit_logs_immutable();
    """,
)

AUDIT_LOG_IMMUTABILITY_DROP_STATEMENTS = (
    "DROP TRIGGER IF EXISTS audit_logs_immutable ON audit_logs;",
    "DROP FUNCTION IF EXISTS audit_logs_immutable();",
)


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Append-only audit log for all significant actions.

    No updates or deletes — immutable record.
    """

    __tablename__ = "audit_logs"

    __table_args__ = (
        # Reads are always scoped (organisation or user) and ordered by recency,
        # so the composite indexes serve the filtered listing endpoint far
        # better than the single-column indexes alone.
        Index("ix_audit_logs_org_created_at", "organisation_id", "created_at"),
        Index("ix_audit_logs_user_created_at", "user_id", "created_at"),
        Index("ix_audit_logs_action_created_at", "action", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} user={self.user_id}>"

    # Prevent updates — this is append-only
    def __setattr__(self, name: str, value: object) -> None:
        if "id" in self.__dict__ and name in (
            "user_id",
            "role",
            "organisation_id",
            "warehouse_id",
            "action",
            "resource_type",
            "resource_id",
            "payload",
            "ip_address",
            "user_agent",
        ):
            raise AttributeError("AuditLog is immutable — updates are not allowed")
        super().__setattr__(name, value)


def _install_audit_immutability(target: Table, connection: Connection, **kwargs: object) -> None:
    """Create the append-only trigger right after ``audit_logs`` is created."""
    if connection.dialect.name != "postgresql":
        return
    for statement in AUDIT_LOG_IMMUTABILITY_STATEMENTS:
        connection.execute(text(statement))


def _remove_audit_immutability(target: Table, connection: Connection, **kwargs: object) -> None:
    """Drop the trigger and its function after ``audit_logs`` is dropped."""
    if connection.dialect.name != "postgresql":
        return
    for statement in AUDIT_LOG_IMMUTABILITY_DROP_STATEMENTS:
        connection.execute(text(statement))


event.listen(AuditLog.__table__, "after_create", _install_audit_immutability)
event.listen(AuditLog.__table__, "after_drop", _remove_audit_immutability)

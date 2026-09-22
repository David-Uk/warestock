"""Add subscription, audit_log, support_flag tables and org status/created_by

Revision ID: 005
Revises: 004
Create Date: 2026-09-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums
    org_status_enum = postgresql.ENUM("active", "suspended", "pending", name="org_status_enum", create_type=False)
    subscription_plan_enum = postgresql.ENUM("trial", "starter", "growth", "enterprise", name="subscription_plan_enum", create_type=False)
    subscription_status_enum = postgresql.ENUM("active", "past_due", "cancelled", name="subscription_status_enum", create_type=False)
    support_flag_status_enum = postgresql.ENUM("open", "resolved", name="support_flag_status_enum", create_type=False)

    org_status_enum.create(op.get_bind(), checkfirst=True)
    subscription_plan_enum.create(op.get_bind(), checkfirst=True)
    subscription_status_enum.create(op.get_bind(), checkfirst=True)
    support_flag_status_enum.create(op.get_bind(), checkfirst=True)

    # Add status and created_by to organisations
    op.add_column("organisations", sa.Column("status", org_status_enum, server_default="active", nullable=False))
    op.add_column("organisations", sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))

    # Create subscriptions table
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True),
        sa.Column("plan", subscription_plan_enum, nullable=False, server_default="trial"),
        sa.Column("status", subscription_status_enum, nullable=False, server_default="active"),
        sa.Column("trial_ends_at", sa.String(50), nullable=True),
        sa.Column("current_period_end", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("payload", postgresql.JSON, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create support_flags table
    op.create_table(
        "support_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("raised_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", support_flag_status_enum, nullable=False, server_default="open"),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("support_flags")
    op.drop_table("audit_logs")
    op.drop_table("subscriptions")

    op.drop_column("organisations", "created_by")
    op.drop_column("organisations", "status")

    postgresql.ENUM(name="support_flag_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="subscription_status_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="subscription_plan_enum").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="org_status_enum").drop(op.get_bind(), checkfirst=True)

"""Add warehouse_role enum and column to users

Revision ID: 003
Revises: 002
Create Date: 2026-09-21
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

from alembic import op

# revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the warehouse_role_enum type
    warehouse_role_enum = ENUM(
        "warehouse_manager",
        "inventory_controller",
        "receiving_associate",
        "dispatch_associate",
        "cycle_count_auditor",
        "shift_supervisor",
        name="warehouse_role_enum",
        create_type=False,
    )
    warehouse_role_enum.create(op.get_bind(), checkfirst=True)

    # Add warehouse_role column to users table
    op.add_column(
        "users",
        sa.Column(
            "warehouse_role",
            warehouse_role_enum,
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "warehouse_role")
    # Note: PostgreSQL doesn't support removing enum types cleanly

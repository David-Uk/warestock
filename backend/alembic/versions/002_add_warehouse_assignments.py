"""Add user_warehouse_assignments table and org_admin role

Revision ID: 002
Revises: 001
Create Date: 2026-09-21
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add org_admin to tenant_role_enum
    op.execute("ALTER TYPE tenant_role_enum ADD VALUE IF NOT EXISTS 'org_admin'")

    # Create user_warehouse_assignments table
    op.create_table(
        "user_warehouse_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "warehouse_id", name="uq_user_warehouse"),
    )


def downgrade() -> None:
    op.drop_table("user_warehouse_assignments")
    # Note: PostgreSQL doesn't support removing enum values

"""Add alerts table

Revision ID: alert_001
Revises: 2bf8b127786a
Create Date: 2026-09-27

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "alert_001"
down_revision: str | None = "2bf8b127786a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("sku_id", sa.UUID(), nullable=False, index=True),
        sa.Column("location_id", sa.UUID(), nullable=False, index=True),
        sa.Column("warehouse_id", sa.UUID(), nullable=False, index=True),
        sa.Column("organisation_id", sa.UUID(), nullable=False, index=True),
        sa.Column(
            "alert_type",
            sa.Enum(
                "low_stock",
                "reorder_needed",
                "discrepancy",
                name="alert_type_enum",
                create_constraint=True,
            ),
            nullable=False,
            server_default="low_stock",
            index=True,
        ),
        sa.Column(
            "severity",
            sa.Enum(
                "low",
                "medium",
                "high",
                "critical",
                name="alert_severity_enum",
                create_constraint=True,
            ),
            nullable=False,
            server_default="medium",
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "acknowledged",
                "dismissed",
                name="alert_status_enum",
                create_constraint=True,
            ),
            nullable=False,
            server_default="active",
            index=True,
        ),
        sa.Column("current_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reorder_threshold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.String(length=500), nullable=True),
        sa.Column("acknowledged_by", sa.UUID(), nullable=True, index=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    # Indexes come from index=True columns (created inline during
    # create_table — matches Base.metadata.create_all naming, e.g.
    # ix_alerts_alert_type).


def downgrade() -> None:
    # drop_table removes the inline (index=True) indexes with the table.
    op.drop_table("alerts")

    bind = op.get_bind()
    sa.Enum("low_stock", "reorder_needed", "discrepancy", name="alert_type_enum").drop(
        bind, checkfirst=True
    )
    sa.Enum("low", "medium", "high", "critical", name="alert_severity_enum").drop(
        bind, checkfirst=True
    )
    sa.Enum("active", "acknowledged", "dismissed", name="alert_status_enum").drop(
        bind, checkfirst=True
    )

"""Add photo_counts and discrepancies tables

Revision ID: 2bf8b127786a
Revises: 009
Create Date: 2026-09-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2bf8b127786a"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "photo_counts",
        sa.Column("warehouse_id", sa.UUID(), nullable=False, index=True),
        sa.Column("location_id", sa.UUID(), nullable=False, index=True),
        sa.Column("organisation_id", sa.UUID(), nullable=False, index=True),
        sa.Column("user_id", sa.UUID(), nullable=True, index=True),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column("photo_public_id", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "analyzing", "completed", "failed", name="photo_count_status_enum", create_constraint=True),
            nullable=False,
            server_default="pending",
            index=True,
        ),
        sa.Column("total_items_detected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("ai_result", sa.JSON(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_photo_counts_location_id"), "photo_counts", ["location_id"])
    op.create_index(op.f("ix_photo_counts_organisation_id"), "photo_counts", ["organisation_id"])
    op.create_index(op.f("ix_photo_counts_status"), "photo_counts", ["status"])
    op.create_index(op.f("ix_photo_counts_user_id"), "photo_counts", ["user_id"])
    op.create_index(op.f("ix_photo_counts_warehouse_id"), "photo_counts", ["warehouse_id"])

    op.create_table(
        "discrepancies",
        sa.Column("photo_count_id", sa.UUID(), nullable=False, index=True),
        sa.Column("sku_id", sa.UUID(), nullable=False, index=True),
        sa.Column("location_id", sa.UUID(), nullable=False, index=True),
        sa.Column("warehouse_id", sa.UUID(), nullable=False, index=True),
        sa.Column("organisation_id", sa.UUID(), nullable=False, index=True),
        sa.Column("system_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detected_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("delta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "severity",
            sa.Enum("low", "medium", "high", "critical", name="discrepancy_severity_enum", create_constraint=True),
            nullable=False,
            server_default="low",
            index=True,
        ),
        sa.Column(
            "status",
            sa.Enum("open", "acknowledged", "resolved", name="discrepancy_status_enum", create_constraint=True),
            nullable=False,
            server_default="open",
            index=True,
        ),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("stock_count_id", sa.UUID(), nullable=True, index=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["photo_count_id"], ["photo_counts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stock_count_id"], ["stock_counts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_discrepancies_location_id"), "discrepancies", ["location_id"])
    op.create_index(op.f("ix_discrepancies_organisation_id"), "discrepancies", ["organisation_id"])
    op.create_index(op.f("ix_discrepancies_photo_count_id"), "discrepancies", ["photo_count_id"])
    op.create_index(op.f("ix_discrepancies_severity"), "discrepancies", ["severity"])
    op.create_index(op.f("ix_discrepancies_sku_id"), "discrepancies", ["sku_id"])
    op.create_index(op.f("ix_discrepancies_status"), "discrepancies", ["status"])
    op.create_index(op.f("ix_discrepancies_warehouse_id"), "discrepancies", ["warehouse_id"])

    op.add_column(
        "stock_counts",
        sa.Column("photo_count_id", sa.UUID(), nullable=True),
    )
    op.create_index(op.f("ix_stock_counts_photo_count_id"), "stock_counts", ["photo_count_id"])
    op.create_foreign_key(
        op.f("fk_stock_counts_photo_count_id_photo_counts"),
        "stock_counts",
        "photo_counts",
        ["photo_count_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_stock_counts_photo_count_id_photo_counts"), "stock_counts", type_="foreignkey")
    op.drop_index(op.f("ix_stock_counts_photo_count_id"), table_name="stock_counts")
    op.drop_column("stock_counts", "photo_count_id")

    op.drop_index(op.f("ix_discrepancies_warehouse_id"), table_name="discrepancies")
    op.drop_index(op.f("ix_discrepancies_status"), table_name="discrepancies")
    op.drop_index(op.f("ix_discrepancies_sku_id"), table_name="discrepancies")
    op.drop_index(op.f("ix_discrepancies_severity"), table_name="discrepancies")
    op.drop_index(op.f("ix_discrepancies_photo_count_id"), table_name="discrepancies")
    op.drop_index(op.f("ix_discrepancies_organisation_id"), table_name="discrepancies")
    op.drop_index(op.f("ix_discrepancies_location_id"), table_name="discrepancies")
    op.drop_table("discrepancies")

    op.drop_index(op.f("ix_photo_counts_warehouse_id"), table_name="photo_counts")
    op.drop_index(op.f("ix_photo_counts_user_id"), table_name="photo_counts")
    op.drop_index(op.f("ix_photo_counts_status"), table_name="photo_counts")
    op.drop_index(op.f("ix_photo_counts_organisation_id"), table_name="photo_counts")
    op.drop_index(op.f("ix_photo_counts_location_id"), table_name="photo_counts")
    op.drop_table("photo_counts")
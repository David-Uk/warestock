"""Add SKU barcode, stock_counts, and sku_embeddings tables

Revision ID: 009
Revises: 008
Create Date: 2026-09-24

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SKU barcode column + per-org uniqueness (multiple NULLs allowed)
    op.add_column("skus", sa.Column("barcode", sa.String(64), nullable=True))
    op.create_index(op.f("ix_skus_barcode"), "skus", ["barcode"], unique=False)
    op.create_unique_constraint("uq_sku_org_barcode", "skus", ["organisation_id", "barcode"])

    # Physical stock counts (scan-count reconciliation records)
    op.create_table(
        "stock_counts",
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("warehouse_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("barcode", sa.String(64), nullable=True),
        sa.Column("system_quantity", sa.Integer(), nullable=False),
        sa.Column("counted_quantity", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("correction_movement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["correction_movement_id"], ["stock_movements.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stock_counts_sku_id"), "stock_counts", ["sku_id"], unique=False)
    op.create_index(
        op.f("ix_stock_counts_location_id"), "stock_counts", ["location_id"], unique=False
    )
    op.create_index(
        op.f("ix_stock_counts_warehouse_id"), "stock_counts", ["warehouse_id"], unique=False
    )
    op.create_index(
        op.f("ix_stock_counts_organisation_id"), "stock_counts", ["organisation_id"], unique=False
    )
    op.create_index(op.f("ix_stock_counts_user_id"), "stock_counts", ["user_id"], unique=False)

    # Vector embeddings for SKU catalogue content (RAG index)
    op.create_table(
        "sku_embeddings",
        sa.Column("organisation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sku_id"], ["skus.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku_id", name="uq_sku_embedding_sku"),
    )
    op.create_index(
        op.f("ix_sku_embeddings_organisation_id"),
        "sku_embeddings",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(op.f("ix_sku_embeddings_sku_id"), "sku_embeddings", ["sku_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sku_embeddings_sku_id"), table_name="sku_embeddings")
    op.drop_index(op.f("ix_sku_embeddings_organisation_id"), table_name="sku_embeddings")
    op.drop_table("sku_embeddings")

    op.drop_index(op.f("ix_stock_counts_user_id"), table_name="stock_counts")
    op.drop_index(op.f("ix_stock_counts_organisation_id"), table_name="stock_counts")
    op.drop_index(op.f("ix_stock_counts_warehouse_id"), table_name="stock_counts")
    op.drop_index(op.f("ix_stock_counts_location_id"), table_name="stock_counts")
    op.drop_index(op.f("ix_stock_counts_sku_id"), table_name="stock_counts")
    op.drop_table("stock_counts")

    op.drop_constraint("uq_sku_org_barcode", "skus", type_="unique")
    op.drop_index(op.f("ix_skus_barcode"), table_name="skus")
    op.drop_column("skus", "barcode")

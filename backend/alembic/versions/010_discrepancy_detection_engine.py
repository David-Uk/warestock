"""Add discrepancy type + resolution audit fields

Revision ID: 010
Revises: alert_001
Create Date: 2026-09-28

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010"
down_revision: str | None = "alert_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

discrepancy_type_enum = sa.Enum(
    "photo_count_mismatch",
    "unauthorized_movement",
    "negative_stock",
    "unusual_movement_pattern",
    name="discrepancy_type_enum",
    create_constraint=True,
)


def upgrade() -> None:
    bind = op.get_bind()

    discrepancy_type_enum.create(bind, checkfirst=True)
    op.add_column(
        "discrepancies",
        sa.Column(
            "discrepancy_type",
            discrepancy_type_enum,
            nullable=False,
            server_default="photo_count_mismatch",
        ),
    )
    op.create_index(
        op.f("ix_discrepancies_discrepancy_type"),
        "discrepancies",
        ["discrepancy_type"],
    )

    # photo_count_id becomes optional (SET NULL) so audit rows survive
    # deletion of the originating photo count.
    op.drop_constraint("discrepancies_photo_count_id_fkey", "discrepancies", type_="foreignkey")
    op.alter_column("discrepancies", "photo_count_id", nullable=True)
    op.create_foreign_key(
        op.f("fk_discrepancies_photo_count_id_photo_counts"),
        "discrepancies",
        "photo_counts",
        ["photo_count_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "discrepancies",
        sa.Column("stock_movement_id", sa.UUID(), nullable=True),
    )
    op.create_index(
        op.f("ix_discrepancies_stock_movement_id"),
        "discrepancies",
        ["stock_movement_id"],
    )
    op.create_foreign_key(
        op.f("fk_discrepancies_stock_movement_id_stock_movements"),
        "discrepancies",
        "stock_movements",
        ["stock_movement_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "discrepancies",
        sa.Column("resolved_by", sa.UUID(), nullable=True),
    )
    op.create_index(op.f("ix_discrepancies_resolved_by"), "discrepancies", ["resolved_by"])
    op.create_foreign_key(
        op.f("fk_discrepancies_resolved_by_users"),
        "discrepancies",
        "users",
        ["resolved_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "discrepancies",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "discrepancies",
        sa.Column("resolution_notes", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("discrepancies", "resolution_notes")
    op.drop_column("discrepancies", "resolved_at")
    op.drop_constraint(
        op.f("fk_discrepancies_resolved_by_users"), "discrepancies", type_="foreignkey"
    )
    op.drop_index(op.f("ix_discrepancies_resolved_by"), table_name="discrepancies")
    op.drop_column("discrepancies", "resolved_by")

    op.drop_constraint(
        op.f("fk_discrepancies_stock_movement_id_stock_movements"),
        "discrepancies",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_discrepancies_stock_movement_id"), table_name="discrepancies")
    op.drop_column("discrepancies", "stock_movement_id")

    op.drop_constraint(
        op.f("fk_discrepancies_photo_count_id_photo_counts"),
        "discrepancies",
        type_="foreignkey",
    )
    # Rows whose photo count was deleted cannot satisfy NOT NULL again.
    op.execute("DELETE FROM discrepancies WHERE photo_count_id IS NULL")
    op.alter_column("discrepancies", "photo_count_id", nullable=False)
    op.create_foreign_key(
        "discrepancies_photo_count_id_fkey",
        "discrepancies",
        "photo_counts",
        ["photo_count_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_index(op.f("ix_discrepancies_discrepancy_type"), table_name="discrepancies")
    op.drop_column("discrepancies", "discrepancy_type")
    discrepancy_type_enum.drop(op.get_bind(), checkfirst=True)

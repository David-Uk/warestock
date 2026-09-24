import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.sku import SKU
    from app.models.warehouse import Warehouse


class StockLevel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Current stock level per SKU+Location+Warehouse."""

    __tablename__ = "stock_levels"

    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Unique constraint: one stock level per SKU+Location+Warehouse
    __table_args__ = (
        UniqueConstraint(
            "warehouse_id", "sku_id", "location_id",
            name="uq_stock_level_warehouse_sku_location",
        ),
    )

    # Relationships (string refs to avoid circular imports)
    sku: Mapped["SKU"] = relationship("SKU", back_populates="stock_levels")
    location: Mapped["Location"] = relationship("Location", back_populates="stock_levels")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="stock_levels")

    def __repr__(self) -> str:
        return f"<StockLevel qty={self.quantity} sku={self.sku_id} loc={self.location_id}>"

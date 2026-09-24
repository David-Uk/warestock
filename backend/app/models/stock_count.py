import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.sku import SKU
    from app.models.warehouse import Warehouse


class StockCount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Physical stock count recorded via barcode scan-count.

    Stores the counted quantity alongside the system (ledger) quantity at the
    time of the count so the delta can be used for reconciliation.
    """

    __tablename__ = "stock_counts"

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
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True)
    system_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    counted_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correction_movement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_movements.id", ondelete="SET NULL"),
        nullable=True,
    )

    sku: Mapped["SKU"] = relationship("SKU")
    location: Mapped["Location"] = relationship("Location")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")

    def __repr__(self) -> str:
        return f"<StockCount sku={self.sku_id} counted={self.counted_quantity} delta={self.delta}>"

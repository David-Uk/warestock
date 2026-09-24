import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_values

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.sku import SKU
    from app.models.user import User
    from app.models.warehouse import Warehouse


class MovementType(str, Enum):
    IN = "in"
    OUT = "out"
    TRANSFER = "transfer"


class StockMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stock movement record — tracks every in/out/transfer action."""

    __tablename__ = "stock_movements"

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
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    movement_type: Mapped[MovementType] = mapped_column(
        SAEnum(
            MovementType,
            name="movement_type_enum",
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
    )
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Relationships (string refs to avoid circular imports)
    sku: Mapped["SKU"] = relationship("SKU", back_populates="stock_movements")
    location: Mapped["Location"] = relationship("Location", back_populates="stock_movements")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="stock_movements")
    user: Mapped["User"] = relationship("User", back_populates="stock_movements")

    def __repr__(self) -> str:
        return f"<StockMovement {self.movement_type.value} qty={self.quantity} sku={self.sku_id}>"

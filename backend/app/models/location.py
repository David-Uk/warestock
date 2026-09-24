import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Location(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Physical storage location within a warehouse (aisle / shelf / bin)."""

    __tablename__ = "locations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aisle: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    shelf: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    bin: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
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

    # Relationships
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    organisation: Mapped["Organisation"] = relationship("Organisation")
    stock_movements: Mapped[list["StockMovement"]] = relationship("StockMovement", back_populates="location")
    stock_levels: Mapped[list["StockLevel"]] = relationship("StockLevel", back_populates="location")

    def __repr__(self) -> str:
        return f"<Location {self.name}>"

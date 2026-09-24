import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organisation import Organisation
    from app.models.stock_level import StockLevel
    from app.models.stock_movement import StockMovement
    from app.models.user_warehouse_assignment import UserWarehouseAssignment


class Warehouse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warehouses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    organisation: Mapped["Organisation"] = relationship(
        "Organisation", back_populates="warehouses"
    )
    user_assignments: Mapped[list["UserWarehouseAssignment"]] = relationship(
        "UserWarehouseAssignment", back_populates="warehouse", cascade="all, delete-orphan"
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship("StockMovement", back_populates="warehouse")
    stock_levels: Mapped[list["StockLevel"]] = relationship("StockLevel", back_populates="warehouse")

    def __repr__(self) -> str:
        return f"<Warehouse {self.name}>"

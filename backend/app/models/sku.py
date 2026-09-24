import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organisation import Organisation
    from app.models.stock_level import StockLevel
    from app.models.stock_movement import StockMovement


class SKU(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Stock Keeping Unit — identifies a unique product within an organisation."""

    __tablename__ = "skus"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    unit_of_measure: Mapped[str] = mapped_column(String(50), nullable=False, default="ea")
    reorder_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    barcode: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # A barcode is unique within an organisation (multiple NULLs allowed).
    __table_args__ = (
        UniqueConstraint("organisation_id", "barcode", name="uq_sku_org_barcode"),
    )

    # Relationships
    organisation: Mapped["Organisation"] = relationship("Organisation")
    stock_movements: Mapped[list["StockMovement"]] = relationship("StockMovement", back_populates="sku")
    stock_levels: Mapped[list["StockLevel"]] = relationship("StockLevel", back_populates="sku")

    def __repr__(self) -> str:
        return f"<SKU {self.name}>"

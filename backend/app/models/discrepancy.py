import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_values

if TYPE_CHECKING:
    from app.models.photo_count import PhotoCount
    from app.models.sku import SKU
    from app.models.stock_count import StockCount
    from app.models.warehouse import Warehouse


class DiscrepancySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DiscrepancyStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Discrepancy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "discrepancies"

    photo_count_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("photo_counts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
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
    system_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detected_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    severity: Mapped[DiscrepancySeverity] = mapped_column(
        SAEnum(
            DiscrepancySeverity,
            name="discrepancy_severity_enum",
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=DiscrepancySeverity.LOW,
        index=True,
    )
    status: Mapped[DiscrepancyStatus] = mapped_column(
        SAEnum(
            DiscrepancyStatus,
            name="discrepancy_status_enum",
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=DiscrepancyStatus.OPEN,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stock_count_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_counts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    photo_count: Mapped["PhotoCount"] = relationship("PhotoCount")
    sku: Mapped["SKU"] = relationship("SKU")
    location: Mapped["Location"] = relationship("Location")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    stock_count: Mapped["StockCount | None"] = relationship(
        "StockCount", back_populates="discrepancy"
    )

    def __repr__(self) -> str:
        return (
            f"<Discrepancy id={self.id} sku={self.sku_id} "
            f"delta={self.delta} severity={self.severity.value}>"
        )

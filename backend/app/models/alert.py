import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_values

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.sku import SKU
    from app.models.warehouse import Warehouse


class AlertType(str, Enum):
    LOW_STOCK = "low_stock"
    REORDER_NEEDED = "reorder_needed"
    DISCREPANCY = "discrepancy"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

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
    alert_type: Mapped[AlertType] = mapped_column(
        SAEnum(
            AlertType,
            name="alert_type_enum",
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        SAEnum(
            AlertSeverity,
            name="alert_severity_enum",
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=AlertSeverity.MEDIUM,
        index=True,
    )
    status: Mapped[AlertStatus] = mapped_column(
        SAEnum(
            AlertStatus,
            name="alert_status_enum",
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=AlertStatus.ACTIVE,
        index=True,
    )
    current_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sku: Mapped["SKU"] = relationship("SKU")
    location: Mapped["Location"] = relationship("Location")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")

    def __repr__(self) -> str:
        return (
            f"<Alert id={self.id} type={self.alert_type.value} "
            f"severity={self.severity.value} sku={self.sku_id}>"
        )

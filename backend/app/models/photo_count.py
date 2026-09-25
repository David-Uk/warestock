import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SAEnum, DateTime, ForeignKey, Float, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_values

if TYPE_CHECKING:
    from app.models.location import Location
    from app.models.user import User
    from app.models.warehouse import Warehouse


class PhotoCountStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class PhotoCount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "photo_counts"

    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
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
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_public_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[PhotoCountStatus] = mapped_column(
        SAEnum(
            PhotoCountStatus,
            name="photo_count_status_enum",
            create_constraint=True,
            values_callable=enum_values,
        ),
        nullable=False,
        default=PhotoCountStatus.PENDING,
        index=True,
    )
    total_items_detected: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    warehouse: Mapped["Warehouse"] = relationship("Warehouse")
    location: Mapped["Location"] = relationship("Location")
    user: Mapped["User | None"] = relationship("User")
    stock_counts: Mapped[list["StockCount"]] = relationship(
        "StockCount", back_populates="photo_count", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PhotoCount id={self.id} status={self.status.value} items={self.total_items_detected}>"

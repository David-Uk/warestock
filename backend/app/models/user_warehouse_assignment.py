import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.warehouse import Warehouse


class UserWarehouseAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Many-to-many relationship between users and warehouses.

    - org_admin: has implicit access to all warehouses (no assignment needed)
    - warehouse_admin: assigned to specific warehouses they manage
    - warehouse_staff: assigned to specific warehouses they work in
    """
    __tablename__ = "user_warehouse_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "warehouse_id", name="uq_user_warehouse"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="warehouse_assignments")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse", back_populates="user_assignments")

    def __repr__(self) -> str:
        return f"<UserWarehouseAssignment user={self.user_id} warehouse={self.warehouse_id}>"

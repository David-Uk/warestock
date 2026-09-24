import uuid
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String, select
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlatformRole(str, Enum):
    SUPERADMIN = "superadmin"
    SYSTEM_ADMIN = "system_admin"
    HELPDESK = "helpdesk"


class TenantRole(str, Enum):
    ORG_ADMIN = "org_admin"
    WAREHOUSE_ADMIN = "warehouse_admin"
    WAREHOUSE_STAFF = "warehouse_staff"


class WarehouseRole(str, Enum):
    """Operational roles for warehouse staff. Required when tenant_role is warehouse_staff."""
    WAREHOUSE_MANAGER = "warehouse_manager"
    INVENTORY_CONTROLLER = "inventory_controller"
    RECEIVING_ASSOCIATE = "receiving_associate"
    DISPATCH_ASSOCIATE = "dispatch_associate"
    CYCLE_COUNT_AUDITOR = "cycle_count_auditor"
    SHIFT_SUPERVISOR = "shift_supervisor"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Role fields
    platform_role: Mapped[PlatformRole | None] = mapped_column(
        SAEnum(PlatformRole, name="platform_role_enum", create_constraint=True),
        nullable=True,
    )
    tenant_role: Mapped[TenantRole | None] = mapped_column(
        SAEnum(TenantRole, name="tenant_role_enum", create_constraint=True),
        nullable=True,
    )
    warehouse_role: Mapped[WarehouseRole | None] = mapped_column(
        SAEnum(WarehouseRole, name="warehouse_role_enum", create_constraint=True),
        nullable=True,
    )

    # Tenant association
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    organisation: Mapped["Organisation | None"] = relationship(
        "Organisation",
        back_populates="users",
        foreign_keys="[User.organisation_id]",
    )
    warehouse_assignments: Mapped[list["UserWarehouseAssignment"]] = relationship(
        "UserWarehouseAssignment", back_populates="user", cascade="all, delete-orphan"
    )
    temporal_permissions: Mapped[list["TemporalPermission"]] = relationship(
        "TemporalPermission",
        foreign_keys="[TemporalPermission.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def is_platform_user(self) -> bool:
        return self.platform_role is not None

    @property
    def is_tenant_user(self) -> bool:
        return self.tenant_role is not None

    @property
    def is_org_admin(self) -> bool:
        return self.tenant_role == TenantRole.ORG_ADMIN

    @property
    def is_warehouse_admin(self) -> bool:
        return self.tenant_role == TenantRole.WAREHOUSE_ADMIN

    @property
    def is_warehouse_staff(self) -> bool:
        return self.tenant_role == TenantRole.WAREHOUSE_STAFF

    async def has_warehouse_access(self, warehouse_id: uuid.UUID, db: AsyncSession) -> bool:
        """Check if user has access to a specific warehouse."""
        from app.models.user_warehouse_assignment import UserWarehouseAssignment
        if self.is_org_admin:
            return True
        result = await db.execute(
            select(UserWarehouseAssignment).where(
                UserWarehouseAssignment.user_id == self.id,
                UserWarehouseAssignment.warehouse_id == warehouse_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_assigned_warehouse_ids(self, db: AsyncSession) -> list[uuid.UUID]:
        """Get list of warehouse IDs this user is assigned to."""
        from app.models.user_warehouse_assignment import UserWarehouseAssignment
        result = await db.execute(
            select(UserWarehouseAssignment.warehouse_id).where(
                UserWarehouseAssignment.user_id == self.id
            )
        )
        return [row[0] for row in result.all()]

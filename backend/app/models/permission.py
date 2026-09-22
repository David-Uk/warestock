import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PermissionScope(str, Enum):
    """Scope of a permission — determines where it applies."""
    PLATFORM = "platform"      # Applies across all tenants (system-level)
    TENANT = "tenant"          # Applies within a single organisation
    WAREHOUSE = "warehouse"    # Applies within a single warehouse


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Defines an atomic permission that can be granted to roles.

    Permissions follow the format: resource:action
    Examples: stock:read, users:manage, warehouses:create
    """
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[PermissionScope] = mapped_column(
        SAEnum(PermissionScope, name="permission_scope_enum", create_constraint=True),
        nullable=False,
    )

    # Relationships
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"


class RolePermission(UUIDPrimaryKeyMixin, Base):
    """Maps a role identifier to a permission.

    The `role_key` is a composite of role_type:role_value, e.g.:
    - platform:superadmin
    - platform:system_admin
    - platform:helpdesk
    - tenant:org_admin
    - tenant:warehouse_admin
    - tenant:warehouse_staff
    - warehouse:warehouse_manager
    - warehouse:inventory_controller
    """
    __tablename__ = "role_permissions"

    role_key: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    permission: Mapped["Permission"] = relationship(
        "Permission", back_populates="role_permissions"
    )

    def __repr__(self) -> str:
        return f"<RolePermission {self.role_key} -> {self.permission_id}>"


class TemporalPermission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Grants a temporary permission to a specific user.

    Used for one-off access grants (e.g., a warehouse staff member
    temporarily granted dispatch permissions for a shift).
    """
    __tablename__ = "temporal_permissions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    granted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="temporal_permissions"
    )
    permission: Mapped["Permission"] = relationship("Permission")
    warehouse: Mapped["Warehouse | None"] = relationship("Warehouse")
    granter: Mapped["User"] = relationship(
        "User", foreign_keys=[granted_by]
    )

    def __repr__(self) -> str:
        return f"<TemporalPermission user={self.user_id} perm={self.permission_id}>"

    @property
    def is_valid(self) -> bool:
        """Check if this temporal permission is currently valid."""
        now = datetime.now(UTC)
        return not self.is_revoked and self.expires_at > now

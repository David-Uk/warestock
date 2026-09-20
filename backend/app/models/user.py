import uuid
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlatformRole(str, Enum):
    SUPERADMIN = "superadmin"
    SYSTEM_ADMIN = "system_admin"
    HELPDESK = "helpdesk"


class TenantRole(str, Enum):
    WAREHOUSE_ADMIN = "warehouse_admin"
    WAREHOUSE_STAFF = "warehouse_staff"


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

    # Tenant association
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    organisation: Mapped["Organisation | None"] = relationship(
        "Organisation", back_populates="users"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def is_platform_user(self) -> bool:
        return self.platform_role is not None

    @property
    def is_tenant_user(self) -> bool:
        return self.tenant_role is not None

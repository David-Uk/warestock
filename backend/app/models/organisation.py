
import uuid
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_values

if TYPE_CHECKING:
    from app.models.subscription import Subscription
    from app.models.user import User
    from app.models.warehouse import Warehouse


class OrgStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"


class Organisation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organisations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    settings: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[OrgStatus] = mapped_column(
        SAEnum(
            OrgStatus,
            name="org_status_enum",
            create_constraint=True,
            values_callable=enum_values,
        ),
        default=OrgStatus.ACTIVE,
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    warehouses: Mapped[list["Warehouse"]] = relationship(
        "Warehouse", back_populates="organisation", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="organisation",
        foreign_keys="[User.organisation_id]",
        cascade="all, delete-orphan",
    )
    subscription: Mapped["Subscription | None"] = relationship(
        "Subscription", back_populates="organisation", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Organisation {self.name} ({self.slug})>"

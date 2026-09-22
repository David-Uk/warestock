import uuid
from enum import Enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SupportFlagStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"


class SupportFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Support flags raised by helpdesk/system_admin/superadmin on organisations."""
    __tablename__ = "support_flags"

    raised_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SupportFlagStatus] = mapped_column(
        SAEnum(SupportFlagStatus, name="support_flag_status_enum", create_constraint=True),
        default=SupportFlagStatus.OPEN,
        nullable=False,
    )
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organisation: Mapped["Organisation"] = relationship("Organisation")
    raiser: Mapped["User | None"] = relationship(
        "User", foreign_keys=[raised_by]
    )
    resolver: Mapped["User | None"] = relationship(
        "User", foreign_keys=[resolved_by]
    )

    def __repr__(self) -> str:
        return f"<SupportFlag {self.subject} ({self.status.value})>"

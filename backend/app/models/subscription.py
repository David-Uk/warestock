import uuid
from enum import Enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SubscriptionPlan(str, Enum):
    TRIAL = "trial"
    STARTER = "starter"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Platform-managed subscription for an organisation."""
    __tablename__ = "subscriptions"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    plan: Mapped[SubscriptionPlan] = mapped_column(
        SAEnum(SubscriptionPlan, name="subscription_plan_enum", create_constraint=True),
        default=SubscriptionPlan.TRIAL,
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus, name="subscription_status_enum", create_constraint=True),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )
    trial_ends_at: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    current_period_end: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    # Relationships
    organisation: Mapped["Organisation"] = relationship("Organisation")

    def __repr__(self) -> str:
        return f"<Subscription {self.plan.value} ({self.status.value})>"

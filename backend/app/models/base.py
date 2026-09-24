import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def enum_values(enum_cls: type[PyEnum]) -> list[str]:
    """values_callable for sa.Enum: persist member *values*, not names.

    Alembic migrations create enum types with the lowercase member values
    (e.g. 'active', 'in'); SQLAlchemy's default is to persist member names
    ('ACTIVE', 'IN'), which would not match. Every SAEnum column must pass
    this callable so app writes and migrations agree.
    """
    return [member.value for member in enum_cls]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

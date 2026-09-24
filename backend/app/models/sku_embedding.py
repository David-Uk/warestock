import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.sku import SKU


class SKUEmbedding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Vector embedding for a SKU's searchable content.

    The embedding is stored as a JSON array of floats so the schema works on
    any PostgreSQL instance (no extension required) and can be swapped for a
    pgvector column later without changing the service interface.
    """

    __tablename__ = "sku_embeddings"

    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    sku: Mapped["SKU"] = relationship("SKU")

    __table_args__ = (
        UniqueConstraint("sku_id", name="uq_sku_embedding_sku"),
    )

    def __repr__(self) -> str:
        return f"<SKUEmbedding sku={self.sku_id} model={self.model} dim={self.dimension}>"

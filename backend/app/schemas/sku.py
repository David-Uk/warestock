import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── Request Schemas ─────────────────────────────────────────────────────────


class SKUCreateRequest(BaseModel):
    """Create a new SKU. organisation_id is derived server-side."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=255)
    unit_of_measure: str = Field(default="ea", max_length=50)
    reorder_threshold: int = Field(default=0, ge=0)


class SKUUpdateRequest(BaseModel):
    """Update an SKU. All fields optional; organisation_id is never accepted."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=255)
    unit_of_measure: str | None = Field(default=None, max_length=50)
    reorder_threshold: int | None = Field(default=None, ge=0)


# ── Response Schemas ────────────────────────────────────────────────────────


class SKUResponse(BaseModel):
    """SKU read response."""

    id: uuid.UUID
    name: str
    description: str | None
    category: str | None
    unit_of_measure: str
    reorder_threshold: int
    organisation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SKUListResponse(BaseModel):
    """Paginated list of SKUs."""

    items: list[SKUResponse]
    total: int
    limit: int
    offset: int

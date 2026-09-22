import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ── Request Schemas ─────────────────────────────────────────────────────────


class LocationCreateRequest(BaseModel):
    """Create a new location. organisation_id is derived server-side."""

    name: str = Field(min_length=1, max_length=255)
    aisle: str | None = Field(default=None, max_length=50)
    shelf: str | None = Field(default=None, max_length=50)
    bin: str | None = Field(default=None, max_length=50)
    warehouse_id: uuid.UUID


class LocationUpdateRequest(BaseModel):
    """Update a location. All fields optional; organisation_id is never accepted."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    aisle: str | None = Field(default=None, max_length=50)
    shelf: str | None = Field(default=None, max_length=50)
    bin: str | None = Field(default=None, max_length=50)
    warehouse_id: uuid.UUID | None = None


# ── Response Schemas ────────────────────────────────────────────────────────


class LocationResponse(BaseModel):
    """Location read response."""

    id: uuid.UUID
    name: str
    aisle: str | None
    shelf: str | None
    bin: str | None
    warehouse_id: uuid.UUID
    organisation_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LocationListResponse(BaseModel):
    """Paginated list of locations."""

    items: list[LocationResponse]
    total: int
    limit: int
    offset: int

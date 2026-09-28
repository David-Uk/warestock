import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DiscrepancyResponse(BaseModel):
    """Discrepancy read response."""

    id: uuid.UUID
    discrepancy_type: str
    photo_count_id: uuid.UUID | None
    stock_count_id: uuid.UUID | None
    stock_movement_id: uuid.UUID | None
    sku_id: uuid.UUID
    location_id: uuid.UUID
    warehouse_id: uuid.UUID
    organisation_id: uuid.UUID
    system_quantity: int
    detected_quantity: int
    delta: int
    severity: str
    status: str
    notes: str | None
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
    resolution_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiscrepancyListResponse(BaseModel):
    """Paginated list of discrepancies."""

    items: list[DiscrepancyResponse]
    total: int
    limit: int
    offset: int


class DiscrepancyResolveRequest(BaseModel):
    """Resolve a discrepancy with an optional resolution note."""

    resolution_notes: str | None = Field(
        None, max_length=500, description="How the discrepancy was resolved"
    )


class DiscrepancyAcknowledgeRequest(BaseModel):
    """Acknowledge a discrepancy."""

    note: str | None = Field(None, max_length=500, description="Optional note")

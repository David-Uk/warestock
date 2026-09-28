import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AlertCreateRequest(BaseModel):
    """Create an alert (used internally by the background job)."""

    sku_id: uuid.UUID = Field(..., description="SKU that triggered the alert")
    location_id: uuid.UUID = Field(..., description="Location of the affected SKU")
    warehouse_id: uuid.UUID = Field(..., description="Warehouse containing the location")
    organisation_id: uuid.UUID = Field(..., description="Organisation owning the alert")
    alert_type: str = Field(
        ..., description="Type of alert: low_stock, reorder_needed, discrepancy"
    )
    severity: str = Field(..., description="Alert severity: low, medium, high, critical")
    current_quantity: int = Field(..., ge=0, description="Current stock quantity")
    reorder_threshold: int = Field(..., ge=0, description="Reorder threshold for the SKU")
    message: str | None = Field(None, description="Human-readable alert message")


class AlertResponse(BaseModel):
    """Alert read response."""

    id: uuid.UUID
    sku_id: uuid.UUID
    location_id: uuid.UUID
    warehouse_id: uuid.UUID
    organisation_id: uuid.UUID
    alert_type: str
    severity: str
    status: str
    current_quantity: int
    reorder_threshold: int
    message: str | None
    acknowledged_by: uuid.UUID | None
    acknowledged_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """Paginated list of alerts."""

    items: list[AlertResponse]
    total: int
    limit: int
    offset: int


class AlertAcknowledgeRequest(BaseModel):
    """Acknowledge an alert."""

    note: str | None = Field(None, description="Optional note for the acknowledgement")


class AlertSummaryResponse(BaseModel):
    """Summary of active alerts."""

    total_active: int
    total_acknowledged: int
    total_dismissed: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
